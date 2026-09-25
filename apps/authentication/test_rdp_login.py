"""Authorization tests; no production database or Windows machine required."""
from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from django.http import Http404
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from authentication.api import rdp_login as api
from authentication.const import ConnectionTokenType
from perms.const import ActionChoices
from terminal.models import Applet, AppletHost
from terminal.serializers.applet_host import DeployOptionsSerializer


class RDPLoginAuthorizationTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = SimpleNamespace(
            id=uuid4(), is_service_account=False, has_perm=Mock(return_value=True),
            is_authenticated=True, is_valid=True,
        )
        self.service = SimpleNamespace(
            id=uuid4(), is_service_account=True, has_perm=Mock(return_value=True),
            is_authenticated=True, is_valid=True,
        )
        self.applet = Mock(name='applet')
        self.applet.name = 'weblite'
        self.host = SimpleNamespace(
            id=uuid4(), name='publish', load='normal', is_active=True, deploy_options={'RDP_TOKEN_LOGIN': True},
            terminal=SimpleNamespace(user_id=self.service.id), address='publish.example.test',
            get_protocol_port=lambda protocol: 3389,
        )
        self.applet.filter_available_hosts.return_value = [self.host]
        self.applet.select_host.return_value = self.host
        self.token = Mock(
            id=uuid4(), user=self.user, user_id=self.user.id,
            personal_credential_id=None, face_monitor_token='', type=ConnectionTokenType.USER,
            date_expired=self.now + timedelta(minutes=5),
            connect_method_object={'type': 'applet', 'value': 'weblite'},
            account_object=SimpleNamespace(secret_type='password'),
        )
        self.token.get_permed_account.return_value = SimpleNamespace(
            actions=ActionChoices.connect, date_expired=self.now + timedelta(hours=1),
        )
        self.ticket = Mock(
            id=uuid4(), connection_token_id=self.token.id, host_id=self.host.id,
            app_name='weblite', consumed_at=None, launched_at=None,
            expires_at=self.now + timedelta(seconds=60), grant_expires_at=None,
        )
        context = patch.object(api, 'tmp_to_root_org', side_effect=nullcontext)
        context.start()
        self.addCleanup(context.stop)

    def invoke(self, view_type, user, data):
        # Test endpoint decisions without entering the DB transaction. Actual
        # row-lock concurrency must additionally run against PostgreSQL/MySQL.
        view = view_type()
        request = SimpleNamespace(user=user, data=data, authenticators=[])
        view.check_permissions(request)
        return view.post.__wrapped__(view, request)

    def test_bearer_requires_random_ticket_not_connection_id(self):
        for value in ['', str(self.token.id), 'jms1_' + 'x' * 42, 'jms1_' + 'x' * 43 + '\n', None]:
            with self.subTest(value=value), self.assertRaises(PermissionDenied):
                api.bearer({'ticket': value}, 'ticket', 'jms1_')
        self.assertEqual(api.bearer({'ticket': 'jms1_' + 'x' * 43}, 'ticket', 'jms1_'),
                         api.digest('jms1_' + 'x' * 43))

    def test_permission_is_rechecked_even_when_token_is_valid(self):
        self.token.get_permed_account.return_value = None
        with self.assertRaises(PermissionDenied):
            api.check_connection(self.token)
        self.token.is_valid.assert_called_once()

    def test_expired_permission_admin_token_and_monitoring_are_rejected(self):
        for changes in [
            {'type': ConnectionTokenType.ADMIN}, {'face_monitor_token': 'monitor'},
            {'connect_method_object': {'type': 'native'}},
        ]:
            with self.subTest(changes=changes), patch.multiple(self.token, **changes), self.assertRaises(PermissionDenied):
                api.check_connection(self.token)
        self.token.get_permed_account.return_value.date_expired = self.now - timedelta(seconds=1)
        with self.assertRaises(PermissionDenied):
            api.check_connection(self.token)

    def test_host_binding_and_feature_flag_are_required(self):
        api.check_host(self.host, self.applet, self.service)
        for user in [self.user, SimpleNamespace(**{**vars(self.service), 'id': uuid4()})]:
            with self.assertRaises(PermissionDenied):
                api.check_host(self.host, self.applet, user)
        self.host.deploy_options['RDP_TOKEN_LOGIN'] = False
        with self.assertRaises(PermissionDenied):
            api.check_host(self.host, self.applet, self.service)

    def test_user_cannot_call_component_endpoints(self):
        for view in [api.RDPLoginRedeemApi, api.RDPLoginLaunchApi]:
            with self.subTest(view=view), self.assertRaises(PermissionDenied):
                self.invoke(view, self.user, {})

    def test_issue_reuses_owned_connection_without_asset_accounts(self):
        with patch.object(api, 'ConnectionToken') as model, \
                patch.object(api, 'RDPLoginTicket') as tickets, \
                patch.object(api, 'get_object_or_404', return_value=self.token) as get, \
                patch.object(api, 'check_connection', return_value=self.applet):
            tickets.objects.filter.return_value.first.return_value = None
            response = self.invoke(api.RDPLoginIssueApi, self.user, {'connection_token_id': str(self.token.id)})
            get.assert_called_once_with(model.objects.select_for_update(), id=self.token.id, user=self.user)
            stored = tickets.objects.create.call_args.kwargs
            self.assertEqual(stored['connection_token'], self.token)
            self.assertEqual(stored['ticket_hash'], api.digest(response.data['ticket']))
            self.assertNotIn('ticket', stored)
            self.assertEqual(response['Cache-Control'], 'no-store')
            self.assertEqual(response.data['remote_app_args'], '--rdp-login')
            self.applet.select_host_account.assert_not_called()
            self.applet.select_host.assert_called_once_with(self.user, self.token.asset, rdp_token_login=True)

    def test_consumed_connection_cannot_get_a_second_ticket(self):
        self.ticket.consumed_at = self.now
        with patch.object(api, 'ConnectionToken'), patch.object(api, 'RDPLoginTicket') as tickets, \
                patch.object(api, 'get_object_or_404', return_value=self.token), \
                patch.object(api, 'check_connection', return_value=self.applet):
            tickets.objects.filter.return_value.first.return_value = self.ticket
            with self.assertRaises(PermissionDenied):
                self.invoke(api.RDPLoginIssueApi, self.user, {'connection_token_id': str(self.token.id)})
            tickets.objects.create.assert_not_called()

    def test_redeem_is_single_use_and_bound_to_host(self):
        with patch.object(api, 'lock_authorization', return_value=(self.token, self.ticket)), \
                patch.object(api, 'get_object_or_404', return_value=self.host), \
                patch.object(api, 'check_connection', return_value=self.applet):
            wrong = SimpleNamespace(**{**vars(self.service), 'id': uuid4()})
            with self.assertRaises(PermissionDenied):
                self.invoke(api.RDPLoginRedeemApi, wrong, {'ticket': 'jms1_' + 'x' * 43})
            self.assertIsNone(self.ticket.consumed_at)
            response = self.invoke(api.RDPLoginRedeemApi, self.service, {'ticket': 'jms1_' + 'x' * 43})
            self.assertEqual(response.data['user_id'], str(self.user.id))
            self.assertEqual(self.ticket.grant_hash, api.digest(response.data['grant']))
            self.assertNotIn('connection', response.data)
            with self.assertRaises(PermissionDenied):
                self.invoke(api.RDPLoginRedeemApi, self.service, {'ticket': 'jms1_' + 'x' * 43})

    def test_expired_ticket_and_grant_never_reveal_credentials(self):
        self.ticket.expires_at = self.now - timedelta(seconds=1)
        self.ticket.consumed_at = self.now
        self.ticket.grant_expires_at = self.now - timedelta(seconds=1)
        with patch.object(api, 'lock_authorization', return_value=(self.token, self.ticket)), \
                patch.object(api, 'ConnectionTokenSecretSerializer') as serializer:
            for view, data in [(api.RDPLoginRedeemApi, {'ticket': 'jms1_' + 'x' * 43}),
                               (api.RDPLoginLaunchApi, {'grant': 'jmsg1_' + 'x' * 43})]:
                with self.subTest(view=view), self.assertRaises(PermissionDenied):
                    self.invoke(view, self.service, data)
            serializer.assert_not_called()

    def test_launch_rechecks_permissions_and_consumes_original_connection(self):
        self.ticket.consumed_at = self.now
        self.ticket.grant_expires_at = self.now + timedelta(seconds=90)
        with patch.object(api, 'lock_authorization', return_value=(self.token, self.ticket)), \
                patch.object(api, 'get_object_or_404', return_value=self.host), \
                patch.object(api, 'check_connection', return_value=self.applet) as check, \
                patch.object(api, 'ConnectionTokenSecretSerializer') as serializer:
            check.side_effect = PermissionDenied()
            with self.assertRaises(PermissionDenied):
                self.invoke(api.RDPLoginLaunchApi, self.service, {'grant': 'jmsg1_' + 'x' * 43})
            serializer.assert_not_called()
            self.token.expire.assert_not_called()
            check.side_effect = None
            serializer.return_value.data = {'user': {'id': str(self.user.id)}}
            response = self.invoke(api.RDPLoginLaunchApi, self.service, {'grant': 'jmsg1_' + 'x' * 43})
            self.assertEqual(response.data['connection'], serializer.return_value.data)
            self.token.expire.assert_called_once()
            with self.assertRaises(PermissionDenied):
                self.invoke(api.RDPLoginLaunchApi, self.service, {'grant': 'jmsg1_' + 'x' * 43})
            serializer.assert_called_once_with(self.token)

    def test_locks_connection_before_rechecking_ticket(self):
        with patch.object(api, 'ConnectionToken') as tokens, patch.object(api, 'RDPLoginTicket') as tickets, \
                patch.object(api, 'get_object_or_404', side_effect=[self.ticket, self.token, Http404]) as get:
            with self.assertRaises(Http404):
                api.lock_authorization(ticket_hash='hash')
            self.assertEqual(get.call_args_list[1].args[0], tokens.objects.select_for_update())
            self.assertEqual(get.call_args_list[2].args[0], tickets.objects.select_for_update())
            self.assertEqual(get.call_args_list[2].kwargs, {'id': self.ticket.id, 'ticket_hash': 'hash'})

    def test_jit_mode_does_not_generate_jumpserver_accounts(self):
        host = AppletHost(deploy_options={'RDP_TOKEN_LOGIN': True}, auto_create_accounts=True)
        with patch.object(AppletHost, 'generate_public_accounts') as public, \
                patch.object(AppletHost, 'generate_private_accounts') as private:
            host.generate_accounts()
            public.assert_not_called()
            private.assert_not_called()
        # SimpleTestCase forbids DB queries, including Account creation here.
        host.generate_private_accounts_by_usernames(['alice'])

    def test_cached_host_uuid_is_reused_and_legacy_hosts_are_excluded(self):
        applet = Applet(name='weblite')
        legacy = SimpleNamespace(id=uuid4(), deploy_options={})
        asset = Mock()
        asset.get_labels.return_value.filter.return_value.values_list.return_value = []
        with patch.object(Applet, 'filter_available_hosts', return_value=[legacy, self.host]), \
                patch('terminal.models.applet.applet.cache') as cache:
            cache.get.return_value = str(self.host.id)
            self.assertIs(applet.select_host(self.user, asset, rdp_token_login=True), self.host)
            cache.set.assert_not_called()

    def test_enabled_deployment_requires_verified_https(self):
        for url, skip in [('http://core', False), ('https://core', True), ('https://[', False)]:
            with self.subTest(url=url, skip=skip):
                serializer = DeployOptionsSerializer(data={
                    'RDP_TOKEN_LOGIN': True, 'CORE_HOST': url, 'IGNORE_VERIFY_CERTS': skip,
                })
                self.assertFalse(serializer.is_valid())
        serializer = DeployOptionsSerializer(data={
            'RDP_TOKEN_LOGIN': True, 'CORE_HOST': 'https://core', 'IGNORE_VERIFY_CERTS': False,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_new_model_matches_migration(self):
        from django.apps import apps
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.state import ProjectState
        migrated = MigrationLoader(None, ignore_no_migrations=True).project_state()
        current = ProjectState.from_apps(apps)
        key = ('authentication', 'rdploginticket')
        self.assertEqual(migrated.models[key], current.models[key])
