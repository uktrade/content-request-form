import json
import datetime as dt

from django import forms
from django.conf import settings

from jira import JIRA
from govuk_forms.forms import GOVUKForm
from govuk_forms import widgets, fields
import requests

from .fields import AVFileField


def create_jira_issue(issue_text, attachments):
    jira_client = JIRA(
        settings.JIRA_URL,
        basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))

    issue_dict = {
        'project': {'id': settings.JIRA_PROJECT_ID},
        'summary': 'New change request',
        'description': issue_text,
        'issuetype': {'name': 'Task'},
    }

    issue = jira_client.create_issue(fields=issue_dict)

    for attachment in attachments:
        jira_client.add_attachment(issue=issue, attachment=attachment, filename=attachment.name)

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
)


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

    action = forms.MultipleChoiceField(
        label='Do you want to add, update or remove content?',
        choices=REASON_CHOICES,
        widget=widgets.CheckboxSelectMultiple(),
        help_text='For GOV.UK updates to existing content - please allow 1 working day. '
                  'For NEW content on GOV.UK and Great.gov, please allow a minimum of 3 '
                  'working days to allow for feedback, approvals and upload.'
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
        required=False
    )

    date_explanation = forms.CharField(
        label='Reason',
        widget=widgets.TextInput()
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
        if date < dt.date.today():
            raise forms.ValidationError('The date cannot be in the past')
        return date

    def formatted_text(self):
        self.cleaned_data['action'] = " / ".join(self.cleaned_data['action'])

        return ('Name: {name}\n'
                'Department: {department}\n'
                'Email: {email}\n'
                'Telephone: {telephone}\n'
                'Action: {action}\n'
                'Description: {description}\n'
                'Due date: {due_date}\n'
                'Due date explanation: {date_explanation}'.format(**self.cleaned_data))

    def create_jira_issue(self):
        """Returns the Jira issue ID"""

        attachments = [value for field, value in self.cleaned_data.items() if field.startswith('attachment') if value]

        jira_id = create_jira_issue(self.formatted_text(), attachments)

        slack_notify(f'new content request: jira ref *{jira_id}*')

        return jira_id
