from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.const import AliasAccount
from accounts.personal_credentials import (
    get_personal_credential_for_use,
    get_personal_credential_permission_context,
    save_personal_credential,
)
from authentication.api.connection_token import ConnectionTokenViewSet
from authentication.models import ConnectionToken
from perms.const import ActionChoices


ACCOUNT_ID = '11111111-1111-4111-8111-111111111111'


class HostedAccount(SimpleNamespace):
    @property
    def full_username(self):
        return f'{self.username}@{self.ds_domain}' if self.ds_domain else self.username


class HostedPersonalCredentialTestCase(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(is_valid=True)
        self.platform_protocol = SimpleNamespace(secret_types=['password', 'ssh_key'])
        self.asset = SimpleNamespace(
            org_id='org', is_active=True,
            protocols=Mock(),
            platform=SimpleNamespace(protocols=Mock()),
        )
        self.asset.protocols.filter.return_value.exists.return_value = True
        self.asset.platform.protocols.filter.return_value.first.return_value = self.platform_protocol
        self.account = HostedAccount(
            alias=ACCOUNT_ID, id=ACCOUNT_ID, username='root', has_secret=False,
            secret='', secret_type='password', actions=ActionChoices.connect, ds_domain='',
            date_expired=timezone.now() + timedelta(hours=1),
        )
        self.context = (self.platform_protocol, self.account)
        self.credential = SimpleNamespace(
            id='credential', username='root', secret_type='ssh_key',
            version=3, secret='saved-private-key',
        )

    def permission_context(self, alias=ACCOUNT_ID):
        with patch('accounts.personal_credentials.PermAssetDetailUtil') as utility:
            utility.return_value.validate_permission.return_value = self.account
            context = get_personal_credential_permission_context(
                self.user, self.asset, 'ssh', account_alias=alias,
            )
            utility.return_value.validate_permission.assert_called_once_with(alias, 'ssh')
            return context

    def test_hosted_account_requires_only_its_own_permission(self):
        self.assertEqual(self.permission_context(), self.context)

    @patch('accounts.personal_credentials.tmp_to_org', return_value=nullcontext())
    @patch('accounts.personal_credentials.PersonalAssetCredential')
    def test_domain_username_matches_the_full_username_shown_to_luna(self, model, _org):
        self.account.ds_domain = 'example.com'
        self.credential.username = 'root@example.com'
        model.objects.filter.return_value.defer.return_value.first.return_value = self.credential
        credential = get_personal_credential_for_use(
            self.user, self.asset, 'ssh', 'credential', permission_context=self.context,
        )
        self.assertIs(credential, self.credential)
        self.credential.username = 'root'
        with self.assertRaises(PermissionDenied):
            get_personal_credential_for_use(
                self.user, self.asset, 'ssh', 'credential', permission_context=self.context,
            )

    def test_rejects_managed_secret_missing_username_certificate_and_expired_permission(self):
        for field, value in (
                ('has_secret', True), ('username', ''),
                ('secret_type', 'ssh_certificate'),
                ('date_expired', timezone.now() - timedelta(seconds=1)),
                ('actions', 0),
        ):
            with self.subTest(field=field):
                previous = getattr(self.account, field)
                setattr(self.account, field, value)
                with self.assertRaises(PermissionDenied):
                    self.permission_context()
                setattr(self.account, field, previous)

    def test_rejects_other_virtual_accounts(self):
        for alias in (AliasAccount.USER, AliasAccount.ANON):
            with self.subTest(alias=alias), self.assertRaises(PermissionDenied):
                self.permission_context(alias)

    @patch('accounts.personal_credentials.tmp_to_org', return_value=nullcontext())
    @patch('accounts.personal_credentials.PersonalAssetCredential')
    def test_use_filters_owner_asset_protocol_version_and_matches_username(self, model, _org):
        queryset = model.objects.filter.return_value
        queryset.filter.return_value = queryset
        queryset.defer.return_value = queryset
        queryset.first.return_value = self.credential
        credential = get_personal_credential_for_use(
            self.user, self.asset, 'ssh', 'credential', version=3,
            permission_context=self.context,
        )
        self.assertIs(credential, self.credential)
        model.objects.filter.assert_called_once_with(
            id='credential', owner=self.user, asset=self.asset,
            protocol='ssh', is_active=True,
        )
        queryset.filter.assert_called_once_with(version=3)
        queryset.defer.assert_called_once_with('_secret')
        self.credential.username = 'admin'
        with self.assertRaises(PermissionDenied) as error:
            get_personal_credential_for_use(
                self.user, self.asset, 'ssh', 'credential',
                permission_context=self.context,
            )
        self.assertEqual(error.exception.get_codes(), 'personal_credential_username_mismatch')

    def test_save_rejects_a_different_username_before_writing(self):
        with self.assertRaises(PermissionDenied):
            save_personal_credential.__wrapped__(
                user=self.user, asset=self.asset, protocol='ssh',
                username='admin', secret='replacement', secret_type='password',
                permission_context=self.context,
            )

    @patch('accounts.personal_credentials.tmp_to_org', return_value=nullcontext())
    @patch('accounts.personal_credentials.PersonalAssetCredential')
    def test_update_cannot_change_another_usernames_credential(self, model, _org):
        self.credential.username = 'admin'
        model.objects.select_for_update.return_value.filter.return_value.first.return_value = self.credential
        with self.assertRaises(PermissionDenied):
            save_personal_credential.__wrapped__(
                user=self.user, asset=self.asset, protocol='ssh',
                username='root', secret='replacement', secret_type='password',
                credential_id='credential', version=3, permission_context=self.context,
            )

    def make_view(self):
        view = ConnectionTokenViewSet()
        view.request = SimpleNamespace(user=self.user)
        view.get_user = Mock(return_value=self.user)
        view._insert_connect_options = Mock()
        view._validate = Mock(return_value={'input_username': ''})
        return view

    @patch('authentication.api.connection_token.get_request_ip_or_data', return_value='127.0.0.1')
    @patch('authentication.api.connection_token.get_personal_credential_permission_context')
    @patch('authentication.api.connection_token.get_personal_credential_for_use')
    def test_token_use_keeps_the_hosted_id_without_copying_the_secret(self, get_credential, get_context, _ip):
        get_context.return_value = self.context
        get_credential.return_value = self.credential
        view = self.make_view()
        data = {
            'asset': self.asset, 'account': ACCOUNT_ID, 'protocol': 'ssh',
            'connect_method': 'web_cli', 'connect_options': {},
            'personal_credential_id': 'credential',
        }
        view.validate_serializer(SimpleNamespace(validated_data=data))
        self.assertEqual(data['account'], ACCOUNT_ID)
        self.assertEqual(data['input_secret'], '')
        self.assertEqual(data['input_secret_type'], 'ssh_key')
        self.assertEqual(data['personal_credential_version'], 3)
        get_context.assert_called_once_with(self.user, self.asset, 'ssh', account_alias=ACCOUNT_ID)
        self.assertIs(view._validate.call_args.kwargs['permed_account'], self.account)

    @patch('authentication.api.connection_token.get_request_ip_or_data', return_value='127.0.0.1')
    @patch('authentication.api.connection_token.get_personal_credential_permission_context')
    @patch('authentication.api.connection_token.save_personal_credential')
    def test_token_save_uses_the_authorized_username_after_acl_validation(self, save, get_context, _ip):
        get_context.return_value = self.context
        save.return_value = self.credential
        view = self.make_view()
        data = {
            'asset': self.asset, 'account': ACCOUNT_ID, 'protocol': 'ssh',
            'connect_method': 'web_cli', 'connect_options': {},
            'save_personal_credential': True,
            'input_username': 'client-supplied-user',
            'input_secret': 'replacement', 'input_secret_type': 'password',
        }
        view.validate_serializer(SimpleNamespace(validated_data=data))
        self.assertEqual(save.call_args.kwargs['username'], 'root')
        self.assertEqual(save.call_args.kwargs['secret'], 'replacement')
        self.assertEqual(data['account'], ACCOUNT_ID)
        self.assertEqual(data['input_secret'], '')

    @patch('authentication.api.connection_token.get_personal_credential_permission_context')
    def test_update_requires_the_credential_version(self, get_context):
        get_context.return_value = self.context
        view = self.make_view()
        with self.assertRaises(ValidationError):
            view.validate_serializer(SimpleNamespace(validated_data={
                'asset': self.asset, 'account': ACCOUNT_ID, 'protocol': 'ssh',
                'connect_method': 'web_cli', 'connect_options': {},
                'save_personal_credential': True, 'personal_credential_id': 'credential',
                'input_secret': 'replacement', 'input_secret_type': 'password',
            }))

    @patch('authentication.api.connection_token.ConnectMethodACL.is_method_allowed', return_value=True)
    def test_ephemeral_hosted_key_type_survives_validation(self, _allowed):
        view = self.make_view()
        del view._validate
        view._validate_acl = Mock(return_value=None)
        data = view._validate(
            self.user, self.asset, ACCOUNT_ID, 'ssh', 'web_cli',
            permed_account=self.account,
        )
        self.assertNotIn('input_secret_type', data)
        self.account.has_secret = True
        data = view._validate(
            self.user, self.asset, ACCOUNT_ID, 'ssh', 'web_cli',
            permed_account=self.account,
        )
        self.assertEqual(data['input_secret_type'], '')

    def test_account_object_overlays_saved_secret_on_the_actual_hosted_account(self):
        token = SimpleNamespace(
            asset=self.asset, account=ACCOUNT_ID, personal_credential_id='credential',
            get_asset_accounts_by_alias=Mock(return_value=self.account),
            get_personal_credential=Mock(return_value=self.credential),
            set_ad_domain_if_need=Mock(),
        )
        result = ConnectionToken.account_object.func(token)
        self.assertIs(result, self.account)
        self.assertEqual(result.id, ACCOUNT_ID)
        self.assertEqual(result.secret, 'saved-private-key')
        self.assertEqual(result.secret_type, 'ssh_key')

    def test_account_object_rejects_a_new_secret_or_changed_username(self):
        for field, value in (('secret', 'managed-secret'), ('username', 'admin')):
            with self.subTest(field=field):
                setattr(self.account, field, value)
                token = SimpleNamespace(
                    asset=self.asset, account=ACCOUNT_ID, personal_credential_id='credential',
                    get_asset_accounts_by_alias=Mock(return_value=self.account),
                    get_personal_credential=Mock(return_value=self.credential),
                )
                with self.assertRaises(PermissionDenied):
                    ConnectionToken.account_object.func(token)
                self.account.secret = ''
                self.account.username = 'root'

    @patch('accounts.personal_credentials.get_personal_credential_permission_context')
    def test_token_revalidates_the_actual_hosted_permission_and_discards_cached_account(self, get_context):
        get_context.return_value = self.context
        token = SimpleNamespace(
            user=self.user, asset=self.asset, protocol='ssh', account=ACCOUNT_ID,
            account_object='stale-account', actions='stale-actions',
            get_personal_credential=Mock(return_value=self.credential),
        )
        ConnectionToken.validate_personal_credential(token)
        get_context.assert_called_once_with(self.user, self.asset, 'ssh', account_alias=ACCOUNT_ID)
        self.assertNotIn('account_object', token.__dict__)
        self.assertNotIn('actions', token.__dict__)
        token.get_personal_credential.assert_called_once_with(
            include_secret=False, permission_context=self.context, force_refresh=True,
        )
