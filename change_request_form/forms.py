import json
import datetime as dt

from django import forms
from django.conf import settings
from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket, CustomField, Comment

from jira import JIRA
from govuk_forms.forms import GOVUKForm
from govuk_forms import widgets, fields
import requests

from .fields import AVFileField


def create_jira_issue(project_id, issue_text, attachments, due_date):
    jira_client = JIRA(
        settings.JIRA_URL,
        basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))

    issue_dict = {
        'project': {'id': project_id},
        'summary': 'New change request',
        'description': issue_text,
        'issuetype': {'name': 'Task'},
        'priority': {'name': 'Medium'},
    }

    if due_date:
        issue_dict['duedate'] = due_date

    issue = jira_client.create_issue(fields=issue_dict)

    for attachment in attachments:
        jira_client.add_attachment(issue=issue, attachment=attachment, filename=attachment.name)

    for watcher_username in settings.JIRA_WATCHERS:
        jira_client.add_watcher(issue, watcher_username)

    return issue.key


def slack_notify(message):
    slack_message = json.dumps(
        {
            'text': message,
            'username': 'contentbot',
            'mrkdwn': True
        }
    ).encode()

    requests.post(settings.SLACK_URL, data=slack_message)


REASON_CHOICES = (
    ('Add new content', 'Add new content'),
    ('Update existing content on Great.gov', 'Update existing content on Great.gov'),
    ('Update existing content on GOV.UK', 'Update existing content on GOV.UK'),
    ('Remove existing content', 'Remove existing content'),
    ('Add new content to Digital Workspace', 'Add new content to Digital Workspace'),
    ('Update or remove content on Digital Workspace', 'Update or remove content on Digital Workspace'),
)


REASON_CHOICES_JIRA_PROJECT_MAP = {
    'Add new content': settings.JIRA_CONTENT_PROJECT_ID,
    'Update existing content on Great.gov': settings.JIRA_CONTENT_PROJECT_ID,
    'Update existing content on GOV.UK': settings.JIRA_CONTENT_PROJECT_ID,
    'Remove existing content': settings.JIRA_CONTENT_PROJECT_ID,
    'Add new content to Digital Workspace': settings.JIRA_WORKSPACE_PROJECT_ID,
    'Update or remove content on Digital Workspace': settings.JIRA_WORKSPACE_PROJECT_ID,
}


class ChangeRequestForm(GOVUKForm):
    name = forms.CharField(
        label='Your full name',
        max_length=255,
        widget=widgets.TextInput()
    )

    department = forms.CharField(
        label='Your directorate/section',
        max_length=255,
        widget=widgets.TextInput(),
        help_text='Your content must have approval from your team leader before submitting for upload.'
    )

    email = forms.EmailField(
        label='Your email address',
        widget=widgets.TextInput()
    )

    telephone = forms.CharField(
        label='Phone number',
        max_length=255,
        widget=widgets.TextInput(),
        help_text='Please provide a direct number in case we need to discuss your request.'
    )

    action = forms.ChoiceField(
        label='Do you want to add, update or remove content?',
        choices=REASON_CHOICES,
        help_text='Please allow a minimum of 3 working days to allow for feedback, approval and upload.'
    )

    description = forms.CharField(
        label='What is your content request? Please give as much detail as possible.',
        widget=widgets.Textarea(),
        help_text='Please outline your request, intended audience and its purpose '
                  '(for example, to sell, to inform, to explain). '
                  'For updating/deleting existing content, please provide URL.'
    )

    due_date = fields.SplitDateField(
        label='Do you have a publication deadline?',
        help_text='If so, give date and reason.',
        required=False,
        min_year=dt.date.today().year,
        max_year=dt.date.today().year + 1,
    )

    date_explanation = forms.CharField(
        label='Reason',
        widget=widgets.TextInput(),
        required=False
    )

    attachment1 = AVFileField(
        label='Please attach the files containing the content you want to be uploaded',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='We accept Word documents with tracked changes - providing this will make the process very quick.',
        required=False
    )

    attachment2 = AVFileField(
        label='',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='',
        required=False
    )

    attachment3 = AVFileField(
        label='',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='',
        required=False
    )

    attachment4 = AVFileField(
        label='',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='',
        required=False
    )

    attachment5 = AVFileField(
        label='',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='',
        required=False
    )

    def clean_due_date(self):
        date = self.cleaned_data['due_date']
        if date and date < dt.date.today():
            raise forms.ValidationError('The date cannot be in the past')
        return date

    def formatted_text(self):
        return ('Name: {name}\n'
                'Department: {department}\n'
                'Email: {email}\n'
                'Telephone: {telephone}\n'
                'Action: {action}\n'
                'Description: {description}\n'
                'Due date: {due_date}\n'
                'Due date explanation: {date_explanation}'.format(**self.cleaned_data))

    def create_jira_issue(self):

        attachments = [value for field, value in self.cleaned_data.items() if field.startswith('attachment') if value]

        project_id = REASON_CHOICES_JIRA_PROJECT_MAP[self.cleaned_data['action']]

        jira_id = create_jira_issue(
            project_id, self.formatted_text(), attachments, str(self.cleaned_data['due_date']))

        jira_url = settings.JIRA_ISSUE_URL.format(jira_id)

        slack_notify(f'new content request: {jira_url}')

        return jira_id

    def create_zendesk_ticket(self):
        zenpy_client = Zenpy(
            subdomain=settings.ZENDESK_SUBDOMAIN,
            email=settings.ZENDESK_EMAIL,
            token=settings.ZENDESK_TOKEN,
        )

        custom_fields = {
            CustomField(id=30041969, value='Content Delivery'),                         # service
            CustomField(id=360000180437, value=self.cleaned_data['department']),        # directorate
            CustomField(id=45522485, value=self.cleaned_data['email']),                 # email
            CustomField(id=360000188178, value=self.cleaned_data['telephone']),         # Phone number
            CustomField(id=360000182638, value=self.cleaned_data['action']),            # Content request
            CustomField(id=360000180457, value=str(self.cleaned_data['due_date'])),     # due date
            CustomField(id=360000180477, value=self.cleaned_data['date_explanation']),  # reason
        }

        ticket = zenpy_client.tickets.create(Ticket(
            subject='Content change request',
            description=self.formatted_text(),
            custom_fields=custom_fields,
            tags=['content delivery']
        )).ticket

        attachments = [value for field, value in self.cleaned_data.items() if field.startswith('attachment') and value]

        if attachments:
            uploads = []
            for attachment in attachments:
                upload_instance = zenpy_client.attachments.upload(attachment.temporary_file_path())
                uploads.append(upload_instance.token)

            ticket.comment = Comment(body=str(attachment), uploads=uploads)

            zenpy_client.tickets.update(ticket)

        slack_notify(f'new content request: {ticket.id}')

        return ticket.id
