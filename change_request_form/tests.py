import datetime as dt

from unittest.mock import patch
from unittest import skip
from django.test import TestCase, Client, override_settings

from .forms import ChangeRequestForm


class BaseTestCase(TestCase):

    def setUp(self):
        self.test_post_data = {
            'name': 'Mr Smith',
            'department': 'test dept',
            'email': 'test@test.com',
            'telephone': '07700 TEST',
            'action': ['Add new content'],
            'description': 'a description',
            'due_date_0': dt.date.today().day,
            'due_date_1': dt.date.today().month,
            'due_date_2': dt.date.today().year,
            'date_explanation': 'ministerial visit',
        }

        test_data = self.test_post_data.copy()

        test_data['action'] = test_data['action'][0]
        test_data['due_date'] = dt.date.today()

        self.test_formatted_text = (
            'Name: {name}\n'
            'Department: {department}\n'
            'Email: {email}\n'
            'Telephone: {telephone}\n'
            'Action: {action}\n'
            'Description: {description}\n'
            'Due date: {due_date}\n'
            'Due date explanation: {date_explanation}').format(**test_data)


class ChangeRequestFormTestCase(BaseTestCase):
    def test_valid_data(self):

        form = ChangeRequestForm(self.test_post_data)
        self.assertTrue(form.is_valid())

    def test_date_in_future(self):
        post_data = {
            'due_date_0': dt.date.today().day - 1,
            'due_date_1': dt.date.today().month,
            'due_date_2': dt.date.today().year,
        }

        form = ChangeRequestForm(post_data)

        self.assertFalse(form.is_valid())
        self.assertIn('due_date', form.errors)
        self.assertEqual(form.errors['due_date'], ['The date cannot be in the past'])

    def test_formatted_text(self):
        form = ChangeRequestForm(self.test_post_data)
        form.is_valid()

        self.assertEqual(
            form.formatted_text(),
            self.test_formatted_text)


class ChangeRequestFormViewTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.client = Client()

    def test_requires_auth(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/auth/login/')

    @patch('authbroker_client.client.has_valid_token')
    @patch('change_request_form.forms.create_jira_issue')
    @patch('change_request_form.forms.slack_notify')
    @skip()
    @override_settings(JIRA_ISSUE_URL='http://jira_url/?selectedIssue={}')
    def test_successful_submission(self, mock_slack_notify, mock_create_jira_issue, mock_has_valid_token):
        mock_has_valid_token.return_value = True
        mock_create_jira_issue.return_value = 'FAKE-JIRA-ID'

        response = self.client.post('/', self.test_post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/success/?issue=FAKE-JIRA-ID')
        self.assertTrue(mock_slack_notify.called)
        mock_slack_notify.call_args.assert_called_with(
            'new content request:http://jira_url/?selectedIssue=FAKE-JIRA-ID')

        self.assertTrue(mock_create_jira_issue.called)
        mock_create_jira_issue.assert_called_with(self.test_formatted_text, [])

    @override_settings(JIRA_ISSUE_URL='http://jira_url/?selectedIssue={}')
    def test_successful_submission(self, mock_slack_notify, mock_create_jira_issue, mock_has_valid_token):
        mock_has_valid_token.return_value = True
        mock_create_jira_issue.return_value = 'FAKE-JIRA-ID'

        response = self.client.post('/', self.test_post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/success/?issue=FAKE-JIRA-ID')
        self.assertTrue(mock_slack_notify.called)
        mock_slack_notify.call_args.assert_called_with(
            'new content request:http://jira_url/?selectedIssue=FAKE-JIRA-ID')

        self.assertTrue(mock_create_jira_issue.called)
        mock_create_jira_issue.assert_called_with(self.test_formatted_text, [])

