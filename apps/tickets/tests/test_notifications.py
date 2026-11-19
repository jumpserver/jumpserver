from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

from django.test import SimpleTestCase
from django.utils.html import escape

from tickets.notifications import BaseTicketMessage, TicketAppliedToAssigneeMessage
from tickets.serializers.ticket.ticket import TicketSerializer


class TicketNotificationTests(SimpleTestCase):
    def test_account_lists_are_readable_without_changing_request_items(self):
        for ticket_type in ('change_secret', 'view_secret'):
            for accounts in (['no_access'], ['no_access', 'ops'], []):
                with self.subTest(ticket_type=ticket_type, accounts=accounts):
                    ticket = SimpleNamespace(type=ticket_type, request_data={'accounts': accounts})
                    before = deepcopy(TicketSerializer.get_request_items(ticket))
                    message = TicketAppliedToAssigneeMessage(None, ticket)
                    values = {item['name']: item['value'] for item in message.spec_items}
                    if accounts:
                        self.assertEqual(values['accounts'], ', '.join(accounts))
                    else:
                        self.assertNotIn('accounts', values)
                    self.assertEqual(TicketSerializer.get_request_items(ticket), before)
                    self.assertIsInstance(before[0]['value'], list)

    def test_other_lists_are_formatted_and_scalar_values_are_preserved(self):
        items = [
            {'name': 'users', 'label': 'Users', 'value': ['Alice', 'Bob']},
            {'name': 'ports', 'label': 'Ports', 'value': [22, 443]},
            {'name': 'duration', 'label': 'Duration', 'value': 0},
            {'name': 'enabled', 'label': 'Enabled', 'value': False},
            {'name': 'comment', 'label': 'Comment', 'value': 'Keep [this] text'},
            {'name': 'empty', 'label': 'Empty', 'value': []},
            {'name': 'missing', 'label': 'Missing', 'value': None},
        ]
        original = deepcopy(items)
        message = TicketAppliedToAssigneeMessage(None, None)
        with patch.object(TicketSerializer, 'get_request_items', return_value=items):
            values = {item['name']: item['value'] for item in message.spec_items}
        self.assertEqual(values, {'users': 'Alice, Bob', 'ports': '22, 443', 'duration': 0,
                                  'enabled': False, 'comment': 'Keep [this] text'})
        self.assertEqual(items, original)

    def test_notification_html_escapes_formatted_account_names(self):
        accounts = ['<img src=x onerror=alert(1)>', 'ops&admin']
        ticket = SimpleNamespace(type='change_secret', request_data={'accounts': accounts},
                                 applicant='Applicant', title='Change password',
                                 get_type_display=lambda: 'Change account password')
        message = TicketAppliedToAssigneeMessage(None, ticket)
        with patch.object(BaseTicketMessage, 'basic_items', new_callable=PropertyMock, return_value=[]):
            rendered = message.gen_html_string()['message']
        self.assertIn(escape(', '.join(accounts)), rendered)
        self.assertNotIn(escape(str(accounts)), rendered)
        self.assertNotIn('<img', rendered)
