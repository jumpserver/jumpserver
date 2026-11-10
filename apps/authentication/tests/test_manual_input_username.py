from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from accounts.const import AliasAccount
from authentication.api.connection_token import ConnectionTokenViewSet


class ManualInputUsernameTests(SimpleTestCase):
    def setUp(self):
        self.view = ConnectionTokenViewSet()
        self.view.request = SimpleNamespace(user=SimpleNamespace(), data={})
        self.view.get_user = Mock(return_value=SimpleNamespace())
        self.view._insert_connect_options = Mock()
        self.view._validate = Mock(return_value={})

    def validate(self, username):
        data = {
            'asset': SimpleNamespace(org_id='org-id'),
            'account': AliasAccount.INPUT,
            'protocol': 'http',
            'connect_method': 'web',
            'connect_options': {},
            'input_username': username,
        }
        serializer = SimpleNamespace(validated_data=data)
        with patch(
            'authentication.api.connection_token.get_effective_connect_options',
            side_effect=lambda options, protocol, asset: options,
        ), patch(
            'authentication.api.connection_token.get_request_ip_or_data',
            return_value='127.0.0.1',
        ):
            self.view.validate_serializer(serializer)
        return data

    def test_empty_username_is_not_replaced_with_input_alias(self):
        data = self.validate('')

        self.assertEqual(self.view.input_username, '')
        self.assertEqual(data['input_username'], '')

    def test_manual_username_is_preserved(self):
        data = self.validate('alice')

        self.assertEqual(self.view.input_username, 'alice')
        self.assertEqual(data['input_username'], 'alice')

    def test_manual_username_still_rejects_forbidden_characters(self):
        with self.assertRaises(ValidationError):
            self.validate('alice|example')
