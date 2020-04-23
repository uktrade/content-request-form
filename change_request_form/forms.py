import json
import datetime as dt

from django import forms
from django.conf import settings
from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket, CustomField, Comment, User

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
    ('digital_workspace', 'workspace.trade.gov.uk (intranet)'),
    ('None', 'None'),
)

REQUEST_TYPE_UPDATE_CHOICE = 'Update page(s)'

REQUEST_TYPE_CHOICES = (
    ('New page(s)', 'New page(s)'),
    (REQUEST_TYPE_UPDATE_CHOICE, 'Update page(s)'),
    ('Other', 'Other'),
)

SERVICE_FIELD_MAPPING = {
    'gov.uk': 'GOV.UK',
    'great.gov.uk': 'Great',
    'digital_workspace': 'Digital Workspace',
    'None': 'None',
}


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
        label='Which platform is the request for? *',
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

    def clean_publication_date(self):
        date = self.cleaned_data['publication_date']
        if date and date < dt.date.today():
            raise forms.ValidationError('The date cannot be in the past')
        return date

    def clean(self):
        cleaned_data = super().clean()

        if 'Update' in cleaned_data.get('request_type', '') and not cleaned_data.get('update_url', ''):
            raise forms.ValidationError('Provide an update url')

    def formatted_text(self, email_id):
        return  """SSO unique id: {email_id}<br>
Name: {name}<br>
Department: {department}<br>
Email: {email}<br>
Telephone: {telephone}<br>
Title of request: {title_of_request}<br>
platform: {platform}<br>
request type: {request_type}<br>
Update urls: {update_url}<br>
Request summary: {request_summary}<br>
User need: {user_need}<br>
Approver: {approver}<br>
Publication date: {publication_date}<br>
Publication date not required?: {publication_date_not_required}<br>
publication date reason: {publication_date_explanation}""".format(
            **{'email_id': email_id, **self.cleaned_data}
        )

    def create_zendesk_ticket(self, sso_email_id):

        zenpy_client = Zenpy(
            subdomain=settings.ZENDESK_SUBDOMAIN,
            email=settings.ZENDESK_EMAIL,
            token=settings.ZENDESK_TOKEN,
        )

        attachments = [value for field, value in self.cleaned_data.items() if field.startswith('attachment') and value]

        if attachments:
            uploads = []
            for attachment in attachments:
                upload_instance = zenpy_client.attachments.upload(attachment.temporary_file_path())
                uploads.append(upload_instance.token)
        else:
            uploads = None

        service = SERVICE_FIELD_MAPPING[self.cleaned_data['platform']]

        custom_fields = [
            CustomField(id=30041969, value=service),                                                # service
            CustomField(id=360000180437, value=self.cleaned_data['department']),                    # directorate
            CustomField(id=45522485, value=self.cleaned_data['email']),                             # email
            CustomField(id=360000188178, value=self.cleaned_data['telephone']),                     # Phone number
            CustomField(id=360000182638, value=self.cleaned_data['request_type']),                  # Content request
            CustomField(id=360000180477, value=self.cleaned_data['publication_date_explanation']),  # reason
        ]

        if not self.cleaned_data['publication_date_not_required']:
            custom_fields.append(
                CustomField(id=360000180457, value=str(self.cleaned_data['publication_date']))  # due date)
            )

        body = self.formatted_text(sso_email_id)

        ticket = zenpy_client.tickets.create(Ticket(
            subject=self.cleaned_data['title_of_request'],
            custom_fields=custom_fields,
            tags=['content_delivery', self.cleaned_data['platform']],
            comment=Comment(html_body=body, uploads=uploads),
            requester=User(name=self.cleaned_data['name'], email=self.cleaned_data['email'])
        )).ticket

        return ticket.id
