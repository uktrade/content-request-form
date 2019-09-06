import json
import datetime as dt

from django import forms
from django.conf import settings
from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket, CustomField, Comment

from govuk_forms.forms import GOVUKForm
from govuk_forms import widgets, fields
import requests


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
    ('Add new content to GOV.UK', 'Add new content to GOV.UK'),
    ('Update or remove content on GOV.UK', 'Update or remove content on GOV.UK'),
    ('Add new content to great.gov.uk', 'Add new content to great.gov.uk'),
    ('Update or remove content on great.gov.uk', 'Update or remove content on great.gov.uk'),
    ('Ask a question', 'Ask a question'),
)

REASON_TO_SERVICE_MAP = {
    'Add new content to GOV.UK': 'GOV.UK',
    'Update or remove content on GOV.UK': 'GOV.UK',
    'Add new content to great.gov.uk': 'great.gov.uk',
    'Update or remove content on great.gov.uk': 'great.gov.uk',
}

ZENDESK_REASON_TO_TAG_MAP = {
    'Add new content to GOV.UK': '_GOV.UK',
    'Update or remove content on GOV.UK': '_GOV.UK',
    'Add new content to great.gov.uk': '_great.gov.uk',
    'Update or remove content on great.gov.uk': '_great.gov.uk',
}


class ChangeRequestForm(GOVUKForm):
    name = forms.CharField(
        label='Your full name',
        max_length=255,
        widget=widgets.TextInput(),
        required=True,
    )

    department = forms.CharField(
        label='Policy team and directorate',
        max_length=255,
        widget=widgets.TextInput(),
        required=True,
    )

    approver = forms.CharField(
        label='Who has approved this request?',
        max_length=255,
        widget=widgets.TextInput(),
        required=True,
    )

    email = forms.EmailField(
        label='Your email address',
        widget=widgets.TextInput(),
        required=True,
    )

    telephone = forms.CharField(
        label='Phone number',
        max_length=255,
        widget=widgets.TextInput(),
        required=False,
    )

    action = forms.ChoiceField(
        label='What do you want to do?',
        choices=REASON_CHOICES,
        widget=widgets.RadioSelect(),
        required=True,
    )

    update_url = forms.URLField(
        label='Provide the URL of the page to be updated', max_length=255,
        widget=widgets.TextInput(),
        help_text='Only required for content updates',
        required=False,
    )

    title_of_request = forms.CharField(
        label='Title of request',
        required=True,
        max_length=100,
        widget=widgets.TextInput(),
    )

    description = forms.CharField(
        label='Summary of your request',
        widget=widgets.Textarea(),
        required=False,
    )

    due_date = fields.SplitDateField(
        label='Publication deadline (if applicable)',
        required=False,
        min_year=dt.date.today().year,
        max_year=dt.date.today().year + 1,
    )

    time_due= forms.CharField(
        label='Is there a specific time that your content needs to go live?',
        required=False,
        max_length=100,
        widget=widgets.TextInput(),
    )

    date_explanation = forms.CharField(
        label='Reason for deadline',
        widget=widgets.TextInput(),
        required=False
    )

    def clean_due_date(self):
        date = self.cleaned_data['due_date']
        if date and date < dt.date.today():
            raise forms.ValidationError('The date cannot be in the past')
        return date

    def clean(self):
        cleaned_data = super().clean()

        if 'Update' in cleaned_data['action'] and not cleaned_data['update_url']:
            raise forms.ValidationError('Provide an update url')

    def formatted_text(self):
        return ('Name: {name}\n'
                'Department: {department}\n'
                'Email: {email}\n'
                'Telephone: {telephone}\n'
                'Action: {action}\n'
                'Description: {description}\n'
                'Due date: {due_date}\n'
                'Time due: {time_due}\n'
                'Due date explanation: {date_explanation}\n'.format(**self.cleaned_data))

    def create_zendesk_ticket(self):
        zenpy_client = Zenpy(
            subdomain=settings.ZENDESK_SUBDOMAIN,
            email=settings.ZENDESK_EMAIL,
            token=settings.ZENDESK_TOKEN,
        )

        service = REASON_TO_SERVICE_MAP[self.cleaned_data['action']]

        custom_fields = [
            CustomField(id=30041969, value=service),                                    # service
            CustomField(id=360000180437, value=self.cleaned_data['department']),        # directorate
            CustomField(id=45522485, value=self.cleaned_data['email']),                 # email
            CustomField(id=360000188178, value=self.cleaned_data['telephone']),         # Phone number
            CustomField(id=360000182638, value=self.cleaned_data['action']),            # Content request
            CustomField(id=360000180477, value=self.cleaned_data['date_explanation']),  # reason
            CustomField(id=360000180457, value=str(self.cleaned_data['due_date']))      # due date
        ]

        tag = ZENDESK_REASON_TO_TAG_MAP[self.cleaned_data['action']]

        ticket = zenpy_client.tickets.create(Ticket(
            subject='Content change request',
            description=self.formatted_text(),
            custom_fields=custom_fields,
            tags=['content delivery', tag]
        )).ticket

        attachments = [value for field, value in self.cleaned_data.items() if field.startswith('attachment') and value]

        if attachments:
            uploads = []
            for attachment in attachments:
                upload_instance = zenpy_client.attachments.upload(attachment.temporary_file_path())
                uploads.append(upload_instance.token)

            ticket.comment = Comment(body=str(attachment), uploads=uploads)

            zenpy_client.tickets.update(ticket)

        return ticket.id
