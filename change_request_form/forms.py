from django import forms
from govuk_forms.forms import GOVUKForm
from govuk_forms import widgets


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

    change_action = forms.ChoiceField(
        label='Do you want to add, update or remove content?',
        choices=REASON_CHOICES,
        widget=widgets.CheckboxSelectMultiple(),
        help_text='For GOV.UK updates to existing content - please allow 1 working day. '
                  'For NEW content on GOV.UK and Great.gov, please allow a minimum of 3 '
                  'working days to allow for feedback, approvals and upload.'
    )

    description = forms.CharField(
        label='What is your content request? Please give as much detail as possible.',
        widget=widgets.TextInput(),
        help_text='Please outline your request, intended audience and it\'s purpose '
                  '(for example, to sell, to inform, to explain). For updating existing '
                  'content, please provide a specific URL to help save time.'

    )

    date = forms.DateField(
        label='When does this need to be published?',
        widget=widgets.SelectDateWidget(),
        help_text='For example, Ministerial visit.'
    )

    date_explanation = forms.CharField(
        label='Please give us a reason for this timeframe',
        widget=widgets.Textarea()
    )

    attachments = forms.FileField(
        label='Please attach supporting Word documents detailing your updates',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='We accept Word documents with track changes - providing this will make the process very quick.'
    )
