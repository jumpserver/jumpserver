"""Core/Tinker v2 authorization decisions, without a Windows host or database."""
import secrets
from contextlib import nullcontext
from datetime import timedelta
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.const import SecretType
from authentication.api import rdp_login as api
from authentication.api import connection_token as token_api
from authentication.api.connection_token import SuperConnectionTokenViewSet
from authentication.const import ConnectionTokenType
from authentication.models import ConnectionToken
from authentication.services import connection_token as token_service
from authentication.services.rdp_login import RDPLoginTicket, TicketCacheUnavailable
from authentication.serializers.rdp_login import RDPLoginRedeemSerializer
from perms.const import ActionChoices
from terminal.models import Applet, AppletHost
from terminal.serializers.applet_host import DeployOptionsSerializer


class RDPLoginAuthorizationTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = SimpleNamespace(
            id=uuid4(), name='张三', username='zhangsan', email='zhangsan@example.com',
            is_service_account=False, has_perm=Mock(return_value=True),
            is_authenticated=True, is_valid=True,
        )
        self.service = SimpleNamespace(
            id=uuid4(), is_service_account=True, has_perm=Mock(return_value=True),
            is_authenticated=True, is_valid=True,
        )
        self.applet = Mock(id=uuid4())
        self.applet.name = 'weblite'
        self.host = SimpleNamespace(
            id=uuid4(), name='publish', load='normal', is_active=True,
            deploy_options={}, tinker_version='v0.3.1',
            terminal=SimpleNamespace(user_id=self.service.id, type='tinker'),
            address='publish.example.test', get_protocol_port=lambda protocol: 3389,
            zone=None, org_id=uuid4(), category='host', type='windows',
            info={}, secret_info={}, spec_info={},
            protocols=[SimpleNamespace(name='rdp', port=3389)],
            platform=SimpleNamespace(
                id=1, name='Windows', category='host', type='windows', package_id=None,
                protocols=[SimpleNamespace(
                    name='rdp', port=3389, primary=True, public=True, required=True,
                    setting={'ad_domain': 'example.org', 'security': 'nla', 'console': False},
                )],
            ),
        )
        self.service.terminal = self.host.terminal
        self.service.terminal.applet_host = self.host
        self.razor = SimpleNamespace(**{**vars(self.service), 'terminal': SimpleNamespace(type='razor')})
        self.applet.filter_available_hosts.return_value = [self.host]
        self.applet.select_host.return_value = self.host
        self.token = Mock(
            id=uuid4(), pk=uuid4(), user=self.user, user_id=self.user.id,
            org_id=uuid4(), asset_id=uuid4(), is_reusable=False,
            personal_credential_id=None, face_monitor_token='', type=ConnectionTokenType.USER,
            date_expired=self.now + timedelta(minutes=10),
            connect_method_object={'type': 'applet', 'value': 'weblite'},
            account_object=SimpleNamespace(secret_type='password'),
        )
        self.token.pk = self.token.id
        self.account = SimpleNamespace(
            actions=ActionChoices.connect, date_expired=self.now + timedelta(hours=1),
        )
        self.token.get_permed_account.return_value = self.account
        self.token.permed_account = self.account
        self.token.get_remote_app_option = lambda: ConnectionToken.get_remote_app_option(self.token)
        self.token.connect_method = 'weblite'
        self.token.asset.id = self.token.asset_id
        self.password = secrets.token_urlsafe(32)
        self.ticket = RDPLoginTicket(
            id=uuid4(), connection_id=uuid4(),
            connection_token_id=self.token.id, org_id=self.token.org_id,
            user_id=self.user.id, asset_id=self.token.asset_id,
            host_id=self.host.id, app_id=self.applet.id, app_name=self.applet.name,
            username='jlt_abcdefghijklmnop',
            password_hash=api.digest('jlt_abcdefghijklmnop\0' + self.password),
            expires_at=self.now + timedelta(minutes=5),
        )
        self.redeem_request = {
            'username': self.ticket.username, 'password': self.password,
        }
        self.connection_data = {
            'id': str(self.token.id), 'org_id': str(self.token.org_id),
            'user': {'id': str(self.user.id)}, 'asset': {'id': str(self.token.asset_id)},
            'account': {'username': 'target-user', 'secret': 'target-secret'},
            'expire_at': int(self.account.date_expired.timestamp()),
        }
        self.cache = Mock()
        self.cache.add.return_value = True
        self.cache.get.side_effect = lambda username: (self.ticket, b'cached-ticket')
        self.cache.consume.side_effect = lambda *args: self.consume_ticket()
        self.consumed = False
        for context in [
            patch.object(api, 'ticket_cache', self.cache),
            patch.object(api, 'tmp_to_root_org', side_effect=nullcontext),
            patch.object(token_api, 'tmp_to_root_org', side_effect=nullcontext),
            patch.object(api.transaction, 'atomic', side_effect=nullcontext),
            patch.object(api.timezone, 'now', return_value=self.now),
        ]:
            context.start()
            self.addCleanup(context.stop)

    def invoke(self, view_type, user, data):
        # Production endpoints retain atomic row locking. These tests isolate
        # authorization decisions; SQL concurrency needs PostgreSQL/MySQL.
        view = view_type()
        request = SimpleNamespace(user=user, data=data, authenticators=[])
        view.check_permissions(request)
        return view.post.__wrapped__(view, request)

    def consume_ticket(self):
        if self.consumed:
            return False
        self.consumed = True
        return True

    def redeem(self, user=None, data=None):
        with patch.object(api, 'get_object_or_404', side_effect=[self.token, self.applet, self.host]), \
                patch.object(api, 'ConnectionTokenSecretSerializer') as serializer, \
                patch.object(ConnectionToken.objects, 'filter'):
            serializer.return_value.data = self.connection_data
            return self.invoke(api.RDPLoginRedeemApi, user or self.service, data or self.redeem_request)

    def applet_option(self, user=None, data=None):
        request = SimpleNamespace(user=user or self.razor, data=data or {'id': str(self.token.id)})
        with patch.object(token_api, 'get_object_or_404', return_value=self.token), \
                patch.object(api, 'get_object_or_404', return_value=self.applet):
            return SuperConnectionTokenViewSet().get_applet_info(request)

    def secret(self, data=None):
        request = SimpleNamespace(
            user=self.razor, data={'id': str(self.token.id), **(data or {})},
        )
        with patch.object(ConnectionToken, 'get_typed_connection_token', return_value=self.token), \
                patch.object(SuperConnectionTokenViewSet, 'get_serializer') as serializer, \
                patch.object(ConnectionToken.objects, 'filter'):
            serializer.return_value.data = self.connection_data
            return SuperConnectionTokenViewSet().get_secret_detail(request)

    def test_only_full_v2_credentials_are_accepted(self):
        for username, password in [
            ('jms1_' + 'a' * 43, self.password), ('jt_abcdefghijklmnop', self.password),
            (self.ticket.username + '\n', self.password), ('jlt_Kbcdefghijklmnopq', self.password),
            (self.ticket.username, ''), (self.ticket.username, str(self.token.id)),
            (self.ticket.username, self.password + '='), (self.ticket.username, 'B' * 43),
            (self.ticket.username, self.password + '\n'),
        ]:
            with self.subTest(username=username, password=password):
                serializer = RDPLoginRedeemSerializer(data={
                    **self.redeem_request, 'username': username, 'password': password,
                })
                self.assertFalse(serializer.is_valid())
        serializer = RDPLoginRedeemSerializer(data={
            **self.redeem_request, 'username': self.ticket.username.upper(),
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['username'], self.ticket.username)

    def test_missing_or_zero_connection_token_ids_are_rejected(self):
        for value in [None, '', 'invalid', str(UUID(int=0))]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.applet_option(data={'id': value})

    def test_permission_is_rechecked_even_for_recent_tokens(self):
        self.token.get_permed_account.return_value = None
        with self.assertRaises(PermissionDenied):
            api.check_connection(self.token)
        self.token.is_valid.assert_called_once_with(include_personal_secret=False)

    def test_expired_permission_admin_token_and_monitoring_are_rejected(self):
        for changes in [
            {'type': ConnectionTokenType.ADMIN}, {'face_monitor_token': 'monitor'},
            {'connect_method_object': {'type': 'native'}},
            {'connect_method_object': {'type': 'applet', 'disabled': True}},
        ]:
            with self.subTest(changes=changes), patch.multiple(self.token, **changes), self.assertRaises(PermissionDenied):
                api.check_connection(self.token)
        self.account.date_expired = self.now
        with self.assertRaises(PermissionDenied):
            api.check_connection(self.token)

    def test_applet_option_returns_ticket_in_existing_account_and_keeps_routing(self):
        self.host.zone = SimpleNamespace(select_gateway=lambda: SimpleNamespace(
            id=uuid4(), name='gateway', address='gateway.example.test', protocols=[], select_account=None,
        ))
        response = self.applet_option()
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(set(response.data), {
            'id', 'applet', 'host', 'gateway', 'platform', 'account', 'remote_app_option',
        })
        credential = response.data['account']
        validator = RDPLoginRedeemSerializer(data={
            **self.redeem_request, 'username': credential['username'], 'password': credential['secret'],
        })
        self.assertTrue(validator.is_valid(), validator.errors)
        stored = self.cache.add.call_args.args[0]
        self.assertEqual(stored.password_hash, api.digest(credential['username'] + '\0' + credential['secret']))
        self.assertNotIn('password', vars(stored))
        self.assertNotEqual(response.data['id'], str(self.token.id))
        self.assertEqual(response.data['host']['id'], str(self.host.id))
        self.assertEqual(response.data['host']['protocols'], [{'name': 'rdp', 'port': 3389}])
        self.assertEqual(response.data['gateway']['address'], 'gateway.example.test')
        self.assertEqual(response.data['platform']['protocols'][0]['setting'], {
            'ad_domain': 'localhost', 'security': 'tls', 'console': False,
        })
        self.assertEqual(self.host.platform.protocols[0].setting['security'], 'nla')
        options = response.data['remote_app_option']
        self.assertEqual(options['remoteapplicationmode:i'], '0')
        self.assertEqual(options['alternate shell:s'], '')
        self.assertNotIn('remoteapplicationprogram:s', options)
        self.assertNotIn('remoteapplicationcmdline:s', options)
        self.applet.select_host.assert_called_once_with(self.user, self.token.asset)

    def test_applet_option_requires_an_authorized_connection_component(self):
        denied = SimpleNamespace(**{**vars(self.razor), 'has_perm': lambda name: False})
        for user in [self.user, self.service, denied]:
            with self.subTest(user=user), self.assertRaises(PermissionDenied):
                self.applet_option(user=user)
        self.cache.add.assert_not_called()
        for component in ['razor', 'koko', 'lion']:
            user = SimpleNamespace(**{**vars(self.razor), 'terminal': SimpleNamespace(type=component)})
            with self.subTest(component=component):
                self.assertEqual(self.applet_option(user=user).status_code, 200)

    def test_ticket_validity_is_capped_at_current_permission_expiration(self):
        self.account.date_expired = self.now + timedelta(seconds=20)
        self.applet_option()
        self.assertEqual(self.cache.add.call_args.args[0].expires_at, self.account.date_expired)

    def test_ticket_can_be_redeemed_just_before_five_minutes(self):
        response = self.applet_option()
        self.ticket = self.cache.add.call_args.args[0]
        self.assertEqual(self.ticket.expires_at, self.now + timedelta(minutes=5))
        # Use the issued account fields, as Razor forwards them to Tinker.
        request = {'username': response.data['account']['username'],
                   'password': response.data['account']['secret']}
        received_at = self.ticket.expires_at - timedelta(microseconds=1)
        with patch.object(api.timezone, 'now', return_value=received_at):
            redeemed = self.redeem(data=request)
        self.assertEqual(redeemed.status_code, 200)
        self.assertEqual(redeemed.data['connection'], self.connection_data)
        self.assertTrue(self.consumed)

    def test_ticket_rejects_exchange_at_or_after_five_minutes(self):
        response = self.applet_option()
        self.ticket = self.cache.add.call_args.args[0]
        request = {'username': response.data['account']['username'],
                   'password': response.data['account']['secret']}
        for delay in [timedelta(minutes=5), timedelta(minutes=5, microseconds=1)]:
            with self.subTest(delay=delay), patch.object(api.timezone, 'now', return_value=self.now + delay):
                with patch.object(api, 'get_connection_token_secret') as secret, self.assertRaises(PermissionDenied):
                    self.redeem(data=request)
                secret.assert_not_called()
        self.cache.consume.assert_not_called()

    def test_successful_exchange_does_not_inherit_ticket_or_token_expiry(self):
        self.token.date_expired = self.now + timedelta(seconds=1)
        self.ticket = replace(self.ticket, expires_at=self.token.date_expired)
        response = self.redeem()
        self.assertNotIn('login_deadline', response.data)
        self.assertEqual(response.data['launch_deadline'], self.account.date_expired.isoformat())

    def test_post_exchange_authorization_still_respects_asset_permission_expiry(self):
        self.account.date_expired = self.now + timedelta(seconds=20)
        response = self.redeem()
        self.assertNotIn('login_deadline', response.data)
        self.assertEqual(response.data['launch_deadline'], self.account.date_expired.isoformat())

    def test_ticket_expiring_during_validation_does_not_disclose_secrets(self):
        self.cache.consume.side_effect = None
        self.cache.consume.return_value = False
        with patch.object(api, 'get_connection_token_secret') as secret, self.assertRaises(PermissionDenied):
            self.redeem()
        secret.assert_not_called()

    def test_ticket_index_collision_is_retried(self):
        self.cache.add.side_effect = [False, True]
        self.applet_option()
        self.assertEqual(self.cache.add.call_count, 2)
        self.assertNotEqual(self.cache.add.call_args_list[0].args[0].username,
                            self.cache.add.call_args_list[1].args[0].username)

    def test_cache_failure_does_not_return_a_credential(self):
        self.cache.add.side_effect = TicketCacheUnavailable()
        with self.assertRaises(TicketCacheUnavailable):
            self.applet_option()
        self.cache.consume.side_effect = TicketCacheUnavailable()
        with patch.object(api, 'get_connection_token_secret') as secret, self.assertRaises(TicketCacheUnavailable):
            self.redeem()
        secret.assert_not_called()

    def test_redeem_returns_tinker_context_and_nested_user(self):
        response = self.redeem()
        for key, value in {
            'attempt_id': self.ticket.id, 'connection_id': self.ticket.connection_id,
            'token_id': self.token.id, 'org_id': self.token.org_id, 'host_id': self.host.id,
            'app_id': self.applet.id, 'target_asset_id': self.token.asset_id,
        }.items():
            self.assertEqual(response.data[key], str(value))
        self.assertEqual(response.data['user'], {
            'id': str(self.user.id), 'name': self.user.name,
            'username': self.user.username, 'email': self.user.email,
        })
        self.assertNotIn('login_deadline', response.data)
        self.assertEqual(response.data['launch_deadline'], self.account.date_expired.isoformat())
        self.assertEqual(response.data['connection'], self.connection_data)
        self.assertNotIn('launch_grant', response.data)
        self.assertEqual(response['Pragma'], 'no-cache')
        self.assertTrue(self.consumed)

    def test_redeem_never_discloses_secrets_twice(self):
        self.redeem()
        with patch.object(api, 'get_connection_token_secret') as secret, self.assertRaises(PermissionDenied):
            self.redeem()
        secret.assert_not_called()

    def test_bad_password_does_not_consume_the_ticket(self):
        with self.assertRaises(PermissionDenied):
            self.redeem(data={**self.redeem_request, 'password': secrets.token_urlsafe(32)})
        self.assertFalse(self.consumed)
        self.redeem()

    def test_host_binding_and_supported_version_are_required(self):
        wrong = SimpleNamespace(**{**vars(self.service), 'id': uuid4()})
        for user in [self.user, wrong]:
            with self.subTest(user=user), self.assertRaises(PermissionDenied):
                self.redeem(user=user)
        self.host.tinker_version = 'v0.3.0'
        with self.assertRaises(PermissionDenied):
            self.redeem()
        self.assertFalse(self.consumed)

    def test_changed_application_user_asset_or_organization_is_rejected(self):
        original = self.ticket
        for key in ['app_id', 'asset_id', 'user_id', 'org_id']:
            self.ticket = replace(original, **{key: uuid4()})
            with self.subTest(key=key), self.assertRaises(PermissionDenied):
                self.redeem()
        self.assertFalse(self.consumed)

    def test_user_cannot_call_component_endpoints(self):
        with self.assertRaises(PermissionDenied):
            self.invoke(api.RDPLoginRedeemApi, self.user, {})
        with patch.object(self.service, 'has_perm', return_value=False), self.assertRaises(PermissionDenied):
            self.redeem()
        self.assertFalse(self.consumed)

    def test_missing_or_expired_ticket_never_redeems(self):
        self.ticket = replace(self.ticket, expires_at=self.now)
        with self.assertRaises(PermissionDenied):
            self.redeem()
        self.cache.get.side_effect = None
        self.cache.get.return_value = None
        with self.assertRaises(PermissionDenied):
            self.redeem()
        self.assertFalse(self.consumed)
        self.token.expire.assert_not_called()

    def test_redeem_rechecks_permissions_before_disclosing_credentials(self):
        self.token.get_permed_account.return_value = None
        with self.assertRaises(PermissionDenied):
            self.redeem()
        self.token.expire.assert_not_called()
        self.assertFalse(self.consumed)

    @override_settings(CONNECTION_TOKEN_REUSABLE=True)
    def test_redeem_consumes_one_time_token_and_returns_matching_tinker_payload(self):
        response = self.redeem()
        self.assertEqual(response.data['connection'], self.connection_data)
        self.token.expire.assert_called_once()
        self.token.is_valid.assert_called_with()
        self.assertTrue(self.consumed)

    @override_settings(CONNECTION_TOKEN_REUSABLE=True)
    def test_reusable_token_survives_consumption_of_one_connection(self):
        self.token.is_reusable = True
        self.redeem()
        self.token.expire.assert_not_called()
        self.assertTrue(self.consumed)

    @override_settings(CONNECTION_TOKEN_REUSABLE=False)
    def test_global_policy_overrides_token_reuse(self):
        self.token.is_reusable = True
        self.redeem()
        self.token.expire.assert_called_once()

    def test_tinker_cannot_skip_consumption_with_expire_now_false(self):
        self.redeem(data={**self.redeem_request, 'expire_now': False})
        self.token.expire.assert_called_once()
        self.assertTrue(self.consumed)

    def test_kubernetes_retains_token_but_cannot_reuse_login_ticket(self):
        for asset_type in ['k8s', 'kubernetes']:
            with self.subTest(asset_type=asset_type):
                self.consumed = False
                self.token.asset.type = asset_type
                response = self.redeem()
                self.assertEqual(response.data['connection'], self.connection_data)
                self.token.expire.assert_not_called()
                self.assertTrue(self.consumed)
                with self.assertRaises(PermissionDenied):
                    self.redeem()

    def test_secret_failure_never_reopens_consumed_ticket(self):
        with patch.object(api, 'get_connection_token_secret', side_effect=PermissionDenied), self.assertRaises(PermissionDenied):
            self.redeem()
        self.assertTrue(self.consumed)
        with patch.object(api, 'get_connection_token_secret') as secret, self.assertRaises(PermissionDenied):
            self.redeem()
        secret.assert_not_called()

    def test_existing_component_secret_response_and_reuse_policy_are_preserved(self):
        response = self.secret(data={'expire_now': False})
        self.assertEqual(response.data, self.connection_data)
        self.assertNotIn('rdp_login', response.data)
        self.token.expire.assert_not_called()

    def test_existing_component_secret_consumes_token_by_default(self):
        self.secret()
        self.token.expire.assert_called_once()

    def test_existing_component_secret_forwards_ssh_public_key(self):
        public_key = 'synthetic-public-key'
        self.token.account_object.secret_type = SecretType.SSH_CERTIFICATE
        certificate = {'signed_key': 'synthetic-certificate', 'serial_number': '1'}
        with patch.object(token_service, 'sign_connection_token_ssh_certificate', return_value=certificate) as sign:
            self.secret(data={'public_key': public_key})
        sign.assert_called_once_with(self.token, public_key)
        self.assertEqual(self.token.account_object.secret, certificate['signed_key'])
        self.assertEqual(self.token.ssh_certificate, {'serial_number': '1'})

    def test_personal_credential_inspection_keeps_existing_audit_semantics(self):
        self.token.personal_credential_id = uuid4()
        with patch.object(token_service, 'record_personal_credential_audit') as audit:
            self.secret(data={'expire_now': False})
        self.token.expire.assert_not_called()
        self.token.is_valid.assert_called_once_with(include_personal_secret=True)
        self.assertEqual(audit.call_args.kwargs['result'], 'inspected')

    def test_only_redemption_has_a_new_rdp_login_route(self):
        from authentication.urls.api_urls import urlpatterns
        routes = [str(pattern.pattern) for pattern in urlpatterns
                  if str(pattern.pattern).startswith('rdp-login/')]
        self.assertEqual(routes, ['rdp-login/redeem/'])

    @override_settings(CONNECTION_TOKEN_REUSABLE=True)
    def test_personal_credential_uses_shared_reuse_policy_and_audit(self):
        self.token.personal_credential_id = uuid4()
        # Creation/update already prohibit reusable personal tokens. The secret
        # API follows the shared dev policy even for a legacy inconsistent flag.
        for reusable in [False, True]:
            with self.subTest(reusable=reusable):
                self.consumed = False
                self.token.expire.reset_mock()
                self.token.is_reusable = reusable
                with patch.object(token_service, 'record_personal_credential_audit') as audit:
                    self.redeem()
                if reusable:
                    self.token.expire.assert_not_called()
                else:
                    self.token.expire.assert_called_once()
                self.assertTrue(self.consumed)
                self.token.is_valid.assert_called_with(include_personal_secret=True)
                self.assertEqual(audit.call_args.kwargs['result'], 'success')
                self.assertEqual(audit.call_args.kwargs['credential_id'], self.token.personal_credential_id)

    def test_each_connection_has_independent_authorization(self):
        self.applet_option()
        self.applet_option()
        first, second = (call.args[0] for call in self.cache.add.call_args_list)
        self.assertEqual(first.connection_token_id, second.connection_token_id)
        self.assertNotEqual(first.id, second.id)
        self.assertNotEqual(first.connection_id, second.connection_id)
        self.assertNotEqual(first.username, second.username)

    def test_ticket_host_cannot_fetch_secrets_with_only_token_id(self):
        view = SuperConnectionTokenViewSet()
        request = SimpleNamespace(user=self.service, data={'id': str(self.token.id)})
        with patch.object(ConnectionToken, 'get_typed_connection_token') as get, self.assertRaises(PermissionDenied):
            view.get_secret_detail(request)
        get.assert_not_called()
        self.assertFalse(api.is_tinker(self.user))
        self.assertFalse(api.is_tinker(self.razor))

    def test_old_account_release_is_compatible_but_generation_is_retired(self):
        from terminal.api.applet.host import AppletHostViewSet
        self.assertEqual(SuperConnectionTokenViewSet().release_applet_account().status_code, 200)
        self.assertEqual(AppletHostViewSet().generate_accounts(None).status_code, 410)

    @override_settings(DEBUG_DEV=False)
    def test_host_selection_excludes_unknown_and_unsupported_tinker_versions(self):
        applet = Applet(name='weblite')
        outdated = SimpleNamespace(id=uuid4(), name='old', tinker_version='v0.3.0', load='normal')
        unknown = SimpleNamespace(id=uuid4(), name='unknown', tinker_version='', load='normal')
        asset = Mock()
        asset.get_labels.return_value.filter.return_value.values_list.return_value = []
        with patch.object(Applet, 'filter_available_hosts', return_value=[outdated, unknown, self.host]), \
                patch.object(Applet, '_select_by_load', side_effect=lambda hosts: hosts[0]), \
                patch('terminal.models.applet.applet.cache') as cache:
            cache.get.return_value = None
            self.assertIs(applet.select_host(self.user, asset), self.host)
        with patch.object(Applet, 'filter_available_hosts', return_value=[outdated, unknown]):
            self.assertIsNone(applet.select_host(self.user, asset))

    def test_incompatible_host_has_an_upgrade_and_redeploy_message(self):
        for version in ['', 'v0.3.0', 'development']:
            with self.subTest(version=version), patch.object(self.host, 'tinker_version', version):
                with self.assertRaisesMessage(PermissionDenied, 'redeploy'):
                    api.check_host(self.host, self.applet, self.service)
        api.check_host(self.host, self.applet, self.service)

    def test_deployment_requires_verified_https(self):
        for url, skip in [('http://core', False), ('https://core', True), ('https://[', False), ('https://@core', False)]:
            with self.subTest(url=url, skip=skip):
                serializer = DeployOptionsSerializer(data={
                    'CORE_HOST': url, 'IGNORE_VERIFY_CERTS': skip,
                })
                self.assertFalse(serializer.is_valid())
        serializer = DeployOptionsSerializer(data={
            'CORE_HOST': 'https://core', 'IGNORE_VERIFY_CERTS': False,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('RDP_TOKEN_LOGIN', serializer.fields)
