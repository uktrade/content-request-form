import json
import datetime as dt

from django import forms
from django.conf import settings
from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket, CustomField, Comment

from govuk_forms.forms import GOVUKForm
from govuk_forms import widgets, fields
import requests

from .fields import AVFileField


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
    ('Add new content to Digital Workspace', 'Add new content to Digital Workspace'),
    ('Update or remove content on Digital Workspace', 'Update or remove content on Digital Workspace'),
)

REASON_TO_SERVICE_MAP = {
    'Add new content to GOV.UK': 'GOV.UK',
    'Update or remove content on GOV.UK': 'GOV.UK',
    'Add new content to great.gov.uk': 'great.gov.uk',
    'Update or remove content on great.gov.uk': 'great.gov.uk',
    'Add new content to Digital Workspace': 'Digital Workspace',
    'Update or remove content on Digital Workspace': 'Digital Workspace',
}

ZENDESK_REASON_TO_TAG_MAP = {
    'Add new content to GOV.UK': '_GOV.UK',
    'Update or remove content on GOV.UK': '_GOV.UK',
    'Add new content to great.gov.uk': '_great.gov.uk',
    'Update or remove content on great.gov.uk': '_great.gov.uk',
    'Add new content to Digital Workspace': 'Digital Workspace',
    'Update or remove content on Digital Workspace': 'Digital Workspace',
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
        help_text='Please allow a minimum of 3 working days to allow for feedback, approval and upload.',
        widget=widgets.RadioSelect(),
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
        required=True,
        min_year=dt.date.today().year,
        max_year=dt.date.today().year + 1,
    )

    time_due= forms.CharField(
        label='Time due',
        required=False,
        max_length=100,
        widget=widgets.TextInput(),
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
