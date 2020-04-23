import datetime as dt

from unittest.mock import patch, Mock
from django.test import TestCase, Client, override_settings
from django.conf import settings

from parameterized import parameterized

from .forms import ChangeRequestForm, REQUEST_TYPE_CHOICES, PLATFORM_CHOICES


class BaseTestCase(TestCase):

    def setUp(self):
        self.test_post_data = {
            'name': 'Mr Smith',
            'department': 'test dept',
            'email': 'test@test.com',
            'telephone': '07700 TEST',
            'title_of_request': 'title of request',
            'platform': PLATFORM_CHOICES[0][0],
            'request_type': REQUEST_TYPE_CHOICES[0][0],
            'update_url': 'http;//google.com',
            'request_summary': 'a summary of the request',
            'user_need': 'user need',
            'approver': 'the approver',
            'publication_date_not_required': True,
            'publication_date_0': dt.date.today().day,
            'publication_date_1': dt.date.today().month,
            'publication_date_2': dt.date.today().year,
            'publication_date_explanation': 'ministerial visit',
        }

        test_data = self.test_post_data.copy()

        test_data['publication_date'] = dt.date.today()

        self.test_formatted_text = """SSO unique id: sso_email_id<br>
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
publication date reason: {publication_date_explanation}""".format(**test_data)



class ChangeRequestFormTestCase(BaseTestCase):
    def test_valid_data(self):

        form = ChangeRequestForm(self.test_post_data)
        self.assertTrue(form.is_valid())

    def test_date_in_future(self):

        previous_date = dt.date.today() - dt.timedelta(days=7)
        post_data = {
            'publication_date_0': previous_date.day,
            'publication_date_1': previous_date.month,
            'publication_date_2': previous_date.year,
        }

        form = ChangeRequestForm(post_data)

        self.assertFalse(form.is_valid())

        self.assertIn('publication_date', form.errors)
        self.assertEqual(form.errors['publication_date'], ['The date cannot be in the past'])

    def test_formatted_text(self):
        form = ChangeRequestForm(self.test_post_data)
        form.is_valid()
        print(form.formatted_text('sso_email_id'))
        print(self.test_formatted_text)

        self.assertEqual(
            form.formatted_text('sso_email_id'),
            self.test_formatted_text)

    def test_due_date_is_optional(self):
        post_data = {k: v for k, v in self.test_post_data.items() if not k.startswith('due_date')}
        form = ChangeRequestForm(post_data)

        self.assertTrue(form.is_valid())

    def test_no_future_limit_on_date(self):
        year = dt.date.today().year
        post_data = self.test_post_data.copy()

        post_data['due_date_2'] = year + 1
        form = ChangeRequestForm(post_data)

        self.assertTrue(form.is_valid())


class ChangeRequestFormViewTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.client = Client()

    def test_requires_auth(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/auth/login/')

    @patch('change_request_form.views.get_profile')
    @patch('authbroker_client.client.has_valid_token')
    @patch('change_request_form.views.slack_notify')
    @patch('change_request_form.forms.Zenpy')
    def test_successful_submission(self, mock_zenpy, mock_slack_notify, mock_has_valid_token, mock_get_profile):
        mock_has_valid_token.return_value = True

        mock_zenpy.return_value.tickets.create.return_value.ticket.id = 12345

        response = self.client.post('/', self.test_post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/success/?issue=12345')
        self.assertTrue(mock_slack_notify.called)
        mock_slack_notify.call_args.assert_called_with(
            'new content request:http://jira_url/?selectedIssue=12345')
