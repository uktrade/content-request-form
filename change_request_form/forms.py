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


PLATFORM_CHOICES = (
    ('gov.uk', 'gov.uk'),
    ('great.gov.uk', 'great.gov.uk'),
    ('workspace.trade.gov.uk', 'workspace.trade.gov.uk (intranet)'),
    ('None', 'None'),
)

REQUEST_TYPE_UPDATE_CHOICE = 'Update page(s)'

REQUEST_TYPE_CHOICES = (
    ('New page(s)', 'New page(s)'),
    (REQUEST_TYPE_UPDATE_CHOICE, 'Update page(s)'),
    ('Other', 'Other'),
)




class ChangeRequestForm(GOVUKForm):
    name = forms.CharField(
        label='Name *',
        max_length=255,
        widget=widgets.TextInput(),
        required=True,
    )

    department = forms.CharField(
        label='Policy team / business area *',
        max_length=255,
        widget=widgets.TextInput(),
        required=True,
    )

    email = forms.EmailField(
        label='Email address *',
        widget=widgets.TextInput(),
        required=True,
    )

    telephone = forms.CharField(
        label='Phone number',
        max_length=255,
        widget=widgets.TextInput(),
        required=False,
    )

    title_of_request = forms.CharField(
        label='Request title *',
        required=True,
        max_length=100,
        widget=widgets.TextInput(),
    )

    platform = forms.ChoiceField(
        label='What do you want to do? *',
        choices=PLATFORM_CHOICES,
        widget=widgets.RadioSelect(),
        required=True,
    )

    request_type = forms.ChoiceField(
        label='What type of request is it? *',
        choices=REQUEST_TYPE_CHOICES,
        widget=widgets.RadioSelect(),
        required=True,
    )

    update_url = forms.CharField(
        label='URL(s) of the page(s) to be updated',
        widget=widgets.Textarea(),
        required=False,
    )

    request_summary = forms.CharField(
        label='Summary of your request *',
        widget=widgets.Textarea(),
        required=True,
    )

    attachment = AVFileField(
        label='Upload an attachment if required',
        help_text='For multiple files, please upload a .zip file',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        required=False
    )

    user_need = forms.CharField(
        label='What user need does this meet? *',
        widget=widgets.Textarea(),
        required=True,
    )

    approver = forms.CharField(
        label='Who has approved (or will sign off) this request? *',
        widget=widgets.TextInput(),
        required=True,
    )

    publication_date = fields.SplitDateField(
        label='Publication deadline',
        required=False,
        min_year=dt.date.today().year,
        max_year=dt.date.today().year + 1,
    )

    publication_date_not_required = forms.BooleanField(
        label='No-date specified',
        widget=widgets.CheckboxInput(),
        required=False,
    )

    publication_date_explanation = forms.CharField(
        label='Provide a reason for this date',
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

        if 'Update' in cleaned_data['request_type'] and not cleaned_data['update_url']:
            raise forms.ValidationError('Provide an update url')

    def formatted_text(self):
        return ('Name: {name}\n'
                'Department: {department}\n'
                'Email: {email}\n'
                'Telephone: {telephone}\n'
                'Title of request: {title_of_request}\n'
                'platform: {olatform}\n',
                'request type: {request_type}\n'
                'Update urls: {update_url}\n'
                'Request summary: {request_summary}\n'
                'User need: {user_need}\n'
                'Approver: {approver} \n'
                'Publication date: {publication_date}\n'
                'Publication date not required?: {publication_date_not_required}\n'
                'publication date reason: {publication_date_explanation}\n'.format(**self.cleaned_data))

    def create_zendesk_ticket(self):
        zenpy_client = Zenpy(
            subdomain=settings.ZENDESK_SUBDOMAIN,
            email=settings.ZENDESK_EMAIL,
            token=settings.ZENDESK_TOKEN,
        )

        custom_fields = [
            CustomField(id=30041969, value=self.cleaned_data['platform']),              # service
            CustomField(id=360000180437, value=self.cleaned_data['department']),        # directorate
            CustomField(id=45522485, value=self.cleaned_data['email']),                 # email
            CustomField(id=360000188178, value=self.cleaned_data['telephone']),         # Phone number
            CustomField(id=360000182638, value=self.cleaned_data['request_type']),      # Content request
            CustomField(id=360000180477, value=self.cleaned_data['publication_date_explanation']),  # reason
            CustomField(id=360000180457, value=str(self.cleaned_data['publication_date']))      # due date
        ]

        ticket = zenpy_client.tickets.create(Ticket(
            subject='Content change request',
            description=self.formatted_text(),
            custom_fields=custom_fields,
            tags=['content delivery', self.cleaned_data['platform']]
        )).ticket

        attachments = [value for field, value in self.cleaned_data.items() if field.startswith('attachment') and value]

        if attachments:
            uploads = []
            for attachment in attachments:
                upload_instance = zenpy_client.attachments.upload(attachment.temporary_file_path())
                uploads.append(upload_instance.token)

            ticket.comment = Comment(body='attachments', uploads=uploads)

            zenpy_client.tickets.update(ticket)

        return ticket.id
