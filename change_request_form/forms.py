from django import forms
from django.conf import settings

from jira import JIRA
from govuk_forms.forms import GOVUKForm
from govuk_forms import widgets, fields

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

    new_issue = jira_client.create_issue(fields=issue_dict)

    # import pdb; pdb.set_trace()

    return f'{new_issue.key}-{new_issue.id}'


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
        label='Your department',
        max_length=255,
        widget=widgets.TextInput(),
        help_text='Your content must have approval from your department before submitting for upload.'
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
        help_text='Please outline your request, intended audience and it\'s purpose '
                  '(for example, to sell, to inform, to explain). For updating existing '
                  'content, please provide a specific URL to help save time.'
    )

    date = fields.SplitDateField(
        label='When does this need to be published?',
        help_text='For example, Ministerial visit.'
    )

    date_explanation = forms.CharField(
        label='Please give us a reason for this timeframe',
        widget=widgets.Textarea()
    )

    attachment1 = AVFileField(
        label='Please attach supporting Word documents detailing your updates',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='We accept Word documents with track changes - providing this will make the process very quick.',
        required=False
    )

    attachment2 = AVFileField(
        label='Please attach supporting Word documents detailing your updates',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='We accept Word documents with track changes - providing this will make the process very quick.',
        required=False
    )

    attachment3 = AVFileField(
        label='Please attach supporting Word documents detailing your updates',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='We accept Word documents with track changes - providing this will make the process very quick.',
        required=False
    )

    attachment4 = AVFileField(
        label='Please attach supporting Word documents detailing your updates',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='We accept Word documents with track changes - providing this will make the process very quick.',
        required=False
    )

    attachment5 = AVFileField(
        label='Please attach supporting Word documents detailing your updates',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='We accept Word documents with track changes - providing this will make the process very quick.',
        required=False
    )

    def formatted_text(self):
        self.cleaned_data['action'] = " / ".join(self.cleaned_data['action'])

        return ('Name: {name}\n'
                'Department: {department}\n'
                'Email: {email}\n'
                'Telephone: {telephone}\n'
                'Action: {action}\n'
                'Description: {description}\n'
                'Due date: {date}\n'
                'Due date explanation: {date_explanation}'.format(**self.cleaned_data))

    def create_jira_issue(self):
        """Returns the Jira issue ID"""
        attachments = [field for field in self.cleaned_data if field.startswith('attachment')]

        return create_jira_issue(self.formatted_text(), attachments)
