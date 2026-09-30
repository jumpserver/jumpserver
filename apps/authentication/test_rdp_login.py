"""Core/Tinker v2 authorization decisions, without a Windows host or database."""
import base64
import json
import secrets
from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from django.db import IntegrityError
from django.http import Http404
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from authentication.api import rdp_login as api
from authentication.api.connection_token import SuperConnectionTokenViewSet
from authentication.const import ConnectionTokenType
from authentication.models import ConnectionToken, RDPLoginTicket
from authentication.serializers.rdp_login import (
    RDPLoginPrepareSerializer, RDPLoginRedeemSerializer, RDPLoginLaunchSerializer,
)
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
        )
        self.service.terminal = self.host.terminal
        self.service.terminal.applet_host = self.host
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
            connection_token_id=self.token.id, org_id=self.token.org_id,
            user_id=self.user.id, asset_id=self.token.asset_id,
            host_id=self.host.id, app_id=self.applet.id, app_name=self.applet.name,
            username='jlt_abcdefghijklmnop',
            password_hash=api.digest('jlt_abcdefghijklmnop\0' + self.password),
            expires_at=self.now + timedelta(minutes=5),
        )
        self.ticket.save = Mock()
        self.broker_id = uuid4()
        self.redeem_request = {
            'username': self.ticket.username, 'password': self.password,
            'redemption_id': str(uuid4()), 'broker_instance_id': str(self.broker_id),
            'windows_session_id': 7,
        }
        self.connection_data = {
            'id': str(self.token.id), 'org_id': str(self.token.org_id),
            'user': {'id': str(self.user.id)}, 'asset': {'id': str(self.token.asset_id)},
        }
        for context in [
            patch.object(api, 'tmp_to_root_org', side_effect=nullcontext),
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

    def redeem(self, user=None, data=None):
        with patch.object(api, 'lock_authorization', return_value=(self.token, self.ticket)), \
                patch.object(api, 'get_object_or_404', side_effect=[self.applet, self.host]):
            return self.invoke(api.RDPLoginRedeemApi, user or self.service, data or self.redeem_request)

    def launch_request(self):
        response = self.redeem()
        return {
            'launch_grant': response.data['launch_grant'], 'token_id': str(self.token.id),
            'connection_id': str(self.ticket.connection_id), 'attempt_id': str(self.ticket.id),
            'request_id': str(uuid4()), 'broker_instance_id': str(self.broker_id),
            'windows_session_id': 7, 'local_sid': 'S-1-5-21-1-2-3-1001', 'logon_id': '00000000:00000400',
        }

    def launch(self, data, user=None):
        with patch.object(api, 'lock_authorization', return_value=(self.token, self.ticket)), \
                patch.object(api, 'get_object_or_404', side_effect=[self.applet, self.host]), \
                patch.object(api, 'ConnectionTokenSecretSerializer') as serializer, \
                patch.object(api.ConnectionToken.objects, 'filter') as query:
            serializer.return_value.data = self.connection_data
            response = self.invoke(api.RDPLoginLaunchApi, user or self.service, data)
            query.return_value.update.assert_called_once_with(date_last_used=self.now)
            return response

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

    def test_missing_or_zero_binding_ids_are_rejected(self):
        for key in ['redemption_id', 'broker_instance_id', 'windows_session_id']:
            for value in [None, 0, str(UUID(int=0))]:
                with self.subTest(key=key, value=value):
                    serializer = RDPLoginRedeemSerializer(data={**self.redeem_request, key: value})
                    self.assertFalse(serializer.is_valid())
        self.assertFalse(RDPLoginPrepareSerializer(data={'connection_token_id': str(UUID(int=0))}).is_valid())

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

    def test_prepare_returns_v2_credentials_and_existing_applet_arguments(self):
        def create(**values):
            values.pop('connection_token')
            return RDPLoginTicket(connection_token_id=self.token.id, **values)
        with patch.object(api, 'get_object_or_404', side_effect=[self.token, self.applet]) as get, \
                patch.object(api.RDPLoginTicket.objects, 'create', side_effect=create) as create_mock:
            response = self.invoke(api.RDPLoginPrepareApi, self.user, {'connection_token_id': str(self.token.id)})
        self.assertEqual(get.call_args_list[0].kwargs, {'id': self.token.id, 'user': self.user})
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.data['credential']['mode'], 'tinker_ticket_v2')
        credential = response.data['credential']
        validator = RDPLoginRedeemSerializer(data={**self.redeem_request, **credential})
        self.assertTrue(validator.is_valid(), validator.errors)
        stored = create_mock.call_args.kwargs
        self.assertEqual(stored['password_hash'], api.digest(credential['username'] + '\0' + credential['password']))
        self.assertNotIn('password', stored)
        ids = [response.data[name] for name in ['attempt_id', 'connection_id', 'token_id']]
        self.assertEqual(len(set(ids)), 3)
        args = json.loads(base64.b64decode(response.data['remote_app']['args']))
        self.assertEqual(args['token_id'], str(self.token.id))
        self.assertEqual(args['app_name'], self.applet.name)
        self.applet.select_host.assert_called_once_with(self.user, self.token.asset)

    def test_prepare_is_restricted_to_token_owner_or_authorized_razor(self):
        for user in [self.service, SimpleNamespace(**{**vars(self.user), 'has_perm': lambda name: False})]:
            with self.subTest(user=user), patch.object(api, 'get_object_or_404') as get, self.assertRaises(PermissionDenied):
                self.invoke(api.RDPLoginPrepareApi, user, {'connection_token_id': str(self.token.id)})
            get.assert_not_called()
        razor = SimpleNamespace(**{**vars(self.service), 'terminal': SimpleNamespace(type='razor')})
        with patch.object(api, 'get_object_or_404', side_effect=[self.token, self.applet]) as get, \
                patch.object(api.RDPLoginTicket.objects, 'create', return_value=self.ticket):
            self.invoke(api.RDPLoginPrepareApi, razor, {'connection_token_id': str(self.token.id)})
        self.assertEqual(get.call_args_list[0].kwargs, {'id': self.token.id})

    def test_prepare_caps_validity_at_current_permission_expiration(self):
        self.account.date_expired = self.now + timedelta(seconds=20)
        with patch.object(api, 'get_object_or_404', side_effect=[self.token, self.applet]), \
                patch.object(api.RDPLoginTicket.objects, 'create', return_value=self.ticket) as create:
            response = self.invoke(api.RDPLoginPrepareApi, self.user, {'connection_token_id': str(self.token.id)})
        self.assertEqual(create.call_args.kwargs['expires_at'], self.account.date_expired)
        self.assertEqual(response.data['credential']['expires_at'], self.account.date_expired.isoformat())

    def test_ticket_index_collision_is_retried(self):
        with patch.object(api, 'get_object_or_404', side_effect=[self.token, self.applet]), \
                patch.object(api.RDPLoginTicket.objects, 'create', side_effect=[IntegrityError(), self.ticket]) as create, \
                patch.object(api.RDPLoginTicket.objects, 'filter') as query:
            query.return_value.exists.return_value = True
            self.invoke(api.RDPLoginPrepareApi, self.user, {'connection_token_id': str(self.token.id)})
        self.assertEqual(create.call_count, 2)
        self.assertNotEqual(create.call_args_list[0].kwargs['username'], create.call_args_list[1].kwargs['username'])

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
        self.assertEqual(self.ticket.grant_hash, api.digest(response.data['launch_grant']))
        self.assertEqual(self.ticket.login_deadline, self.now + timedelta(seconds=90))
        self.assertEqual(self.ticket.launch_deadline, self.now + timedelta(minutes=5))
        self.assertNotIn('connection', response.data)
        self.assertNotIn('grant', response.data)
        self.assertEqual(response['Pragma'], 'no-cache')

    def test_redeem_does_not_release_a_second_grant(self):
        self.redeem()
        with self.assertRaises(PermissionDenied):
            self.redeem()

    def test_bad_password_does_not_consume_the_ticket(self):
        with self.assertRaises(PermissionDenied):
            self.redeem(data={**self.redeem_request, 'password': secrets.token_urlsafe(32)})
        self.assertIsNone(self.ticket.redeemed_at)
        self.redeem()

    def test_host_binding_and_supported_version_are_required(self):
        wrong = SimpleNamespace(**{**vars(self.service), 'id': uuid4()})
        for user in [self.user, wrong]:
            with self.subTest(user=user), self.assertRaises(PermissionDenied):
                self.redeem(user=user)
        self.host.tinker_version = 'v0.3.0'
        with self.assertRaises(PermissionDenied):
            self.redeem()
        self.assertIsNone(self.ticket.redeemed_at)

    def test_changed_application_user_asset_or_organization_is_rejected(self):
        for key in ['app_id', 'asset_id', 'user_id', 'org_id']:
            with self.subTest(key=key), patch.object(self.ticket, key, uuid4()), self.assertRaises(PermissionDenied):
                self.redeem()
        self.assertIsNone(self.ticket.redeemed_at)

    def test_duplicate_redemption_context_is_rejected(self):
        self.ticket.save.side_effect = IntegrityError()
        with self.assertRaises(PermissionDenied):
            self.redeem()

    def test_user_cannot_call_component_endpoints(self):
        for view in [api.RDPLoginRedeemApi, api.RDPLoginLaunchApi]:
            with self.subTest(view=view), self.assertRaises(PermissionDenied):
                self.invoke(view, self.user, {})

    def test_expired_ticket_never_redeems(self):
        self.ticket.expires_at = self.now
        with self.assertRaises(PermissionDenied):
            self.redeem()

    def test_launch_rejects_mismatched_session_and_authorization_ids(self):
        data = self.launch_request()
        for key, value in {
            'token_id': str(uuid4()), 'connection_id': str(uuid4()),
            'broker_instance_id': str(uuid4()), 'windows_session_id': 8,
            'launch_grant': 'jmsg2_' + secrets.token_urlsafe(32),
        }.items():
            with self.subTest(key=key), self.assertRaises(PermissionDenied):
                self.launch({**data, key: value})
        self.assertIsNone(self.ticket.launched_at)
        self.token.expire.assert_not_called()

    def test_launch_requires_real_local_windows_identity(self):
        data = self.launch_request()
        for key, value in [('local_sid', 'S-1-5-18'), ('local_sid', ''), ('logon_id', ''), ('logon_id', '\n')]:
            serializer = RDPLoginLaunchSerializer(data={**data, key: value})
            self.assertFalse(serializer.is_valid(), (key, value))

    def test_expired_launch_grant_never_returns_secrets(self):
        data = self.launch_request()
        self.ticket.launch_deadline = self.now
        with self.assertRaises(PermissionDenied):
            self.launch(data)
        self.token.expire.assert_not_called()

    def test_launch_rechecks_permissions_before_disclosing_credentials(self):
        data = self.launch_request()
        self.token.get_permed_account.return_value = None
        with self.assertRaises(PermissionDenied):
            self.launch(data)
        self.token.expire.assert_not_called()
        self.assertIsNone(self.ticket.launched_at)

    @override_settings(CONNECTION_TOKEN_REUSABLE=True)
    def test_launch_consumes_one_time_token_and_returns_matching_tinker_payload(self):
        data = self.launch_request()
        response = self.launch(data)
        self.assertEqual(response.data, {
            'attempt_id': str(self.ticket.id), 'app_id': str(self.applet.id),
            'app_name': self.applet.name, 'connection': self.connection_data,
        })
        self.token.expire.assert_called_once()
        self.token.is_valid.assert_called_with(include_personal_secret=True)
        self.assertIsNone(self.ticket.grant_hash)
        self.assertEqual(self.ticket.request_id, UUID(data['request_id']))
        self.assertEqual(self.ticket.local_sid, data['local_sid'])
        self.assertEqual(self.ticket.logon_id, data['logon_id'])
        with self.assertRaises(PermissionDenied):
            self.launch(data)

    @override_settings(CONNECTION_TOKEN_REUSABLE=True)
    def test_reusable_token_survives_consumption_of_one_connection(self):
        self.token.is_reusable = True
        data = self.launch_request()
        self.launch(data)
        self.token.expire.assert_not_called()
        self.assertIsNotNone(self.ticket.launched_at)

    @override_settings(CONNECTION_TOKEN_REUSABLE=False)
    def test_global_policy_overrides_token_reuse(self):
        self.token.is_reusable = True
        self.launch(self.launch_request())
        self.token.expire.assert_called_once()

    def test_each_connection_has_independent_authorization(self):
        other = RDPLoginTicket(connection_token_id=self.token.id)
        self.assertNotEqual(self.ticket.id, other.id)
        self.assertNotEqual(self.ticket.connection_id, other.connection_id)
        field = RDPLoginTicket._meta.get_field('connection_token')
        self.assertFalse(field.unique)

    def test_locks_connection_before_ticket_for_both_lookup_modes(self):
        for lookup in [{'username': self.ticket.username}, {'id': self.ticket.id}]:
            with patch.object(api, 'get_object_or_404', side_effect=[self.ticket, self.token, self.ticket]) as get:
                self.assertEqual(api.lock_authorization(**lookup), (self.token, self.ticket))
                self.assertEqual(get.call_args_list[1].kwargs, {'id': self.token.id})
                self.assertEqual(get.call_args_list[2].kwargs, {**lookup, 'id': self.ticket.id})
        with patch.object(api, 'get_object_or_404', side_effect=[self.ticket, self.token, Http404]):
            with self.assertRaises(Http404):
                api.lock_authorization(username=self.ticket.username)

    def test_ticket_host_cannot_use_legacy_secret_endpoint(self):
        view = SuperConnectionTokenViewSet()
        request = SimpleNamespace(user=self.service, data={'id': str(self.token.id)})
        with patch.object(ConnectionToken, 'get_typed_connection_token') as get, self.assertRaises(PermissionDenied):
            view.get_secret_detail(request)
        get.assert_not_called()
        api.check_legacy_secret_access(self.user)
        razor = SimpleNamespace(**{**vars(self.service), 'terminal': SimpleNamespace(type='razor')})
        api.check_legacy_secret_access(razor)

    def test_old_applet_account_endpoints_request_migration(self):
        from terminal.api.applet.host import AppletHostViewSet
        self.assertEqual(SuperConnectionTokenViewSet().get_applet_info().status_code, 410)
        self.assertEqual(SuperConnectionTokenViewSet().release_applet_account().status_code, 410)
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

    def test_enabled_deployment_requires_verified_https(self):
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

    def test_model_matches_migration_and_graph_has_one_leaf(self):
        from django.apps import apps
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.state import ProjectState
        loader = MigrationLoader(None, ignore_no_migrations=True)
        self.assertFalse(loader.detect_conflicts())
        migrated = loader.project_state()
        current = ProjectState.from_apps(apps)
        key = ('authentication', 'rdploginticket')
        self.assertEqual(migrated.models[key], current.models[key])
        self.assertEqual(
            migrated.models[('terminal', 'applethost')].fields['tinker_version'].deconstruct(),
            current.models[('terminal', 'applethost')].fields['tinker_version'].deconstruct(),
        )
