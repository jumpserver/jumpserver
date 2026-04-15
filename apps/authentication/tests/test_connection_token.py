from unittest.mock import Mock, patch

from django.test import TestCase

from accounts.const import AliasAccount, SecretType
from assets.models import Asset
from authentication.models import ConnectionToken


class ConnectionTokenInputSecretTypeTestCase(TestCase):
    def test_input_secret_type_default_password(self):
        token = ConnectionToken(connect_options={})
        self.assertEqual(token.input_secret_type, SecretType.PASSWORD)

    def test_account_object_manual_input_supports_ssh_key(self):
        token = ConnectionToken(
            account=AliasAccount.INPUT,
            input_username=AliasAccount.INPUT,
            input_secret='-----BEGIN OPENSSH PRIVATE KEY-----\n...',
            connect_options={'input_secret_type': SecretType.SSH_KEY},
            asset=Asset(),
            user=Mock(),
        )
        account = Mock(secret_type=SecretType.PASSWORD)

        with patch(
            'authentication.models.connection_token.VirtualAccount.get_special_account',
            return_value=account
        ):
            result = token.account_object

        self.assertEqual(result.secret_type, SecretType.SSH_KEY)

    def test_account_object_input_secret_type_applies_when_account_secret_empty(self):
        token = ConnectionToken(
            account='db_user',
            input_secret='-----BEGIN OPENSSH PRIVATE KEY-----\n...',
            connect_options={'input_secret_type': SecretType.SSH_KEY},
            asset=Asset(),
        )
        account = Mock(secret='', secret_type=SecretType.PASSWORD)

        with patch.object(ConnectionToken, 'get_asset_accounts_by_alias', return_value=account), \
                patch.object(ConnectionToken, 'set_ad_domain_if_need'):
            result = token.account_object

        self.assertEqual(result.secret, token.input_secret)
        self.assertEqual(result.secret_type, SecretType.SSH_KEY)
