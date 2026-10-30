import uuid
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit

from django.db import transaction
from django.test import TestCase
from django.urls import resolve
from django.utils import timezone
from oauth2_provider.models import (
    get_application_model, get_access_token_model, get_grant_model, get_refresh_token_model,
)
from oauthlib.common import Request as OAuthRequest
from oauthlib.oauth2 import InvalidGrantError, InvalidScopeError
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory, force_authenticate

from audits.models import OperateLog
from authentication.backends.oauth2_provider.agent import AgentOAuth2Validator
from authentication.services.agent_clients import AgentClientCleanupBusy, AgentClientCleanupUnavailable
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from rbac.models import Permission, Role
from terminal import agent_service
from terminal.models import AgentApplication, AgentOAuthBinding, AgentSession, AgentAction, AgentEvent, Terminal
from users.models import User


class AgentClientManagementTests(TestCase):
    url = '/api/v1/authentication/agent-clients/'

    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create(username='agent-client-manager')
        cls.user = User.objects.create(username='agent-client-user')
        cls.org_manager = User.objects.create(username='agent-client-org-manager')
        cls.org = Organization.objects.create(name='Agent client management org')
        permission = Permission.objects.get(content_type__app_label='settings', codename='change_auth')
        system_role = Role.objects.create(name='Agent client platform manager', scope='system')
        system_role.permissions.add(permission)
        cls.manager.system_roles.add(system_role)
        org_role = Role.objects.create(name='Agent client organization manager', scope='org')
        org_role.permissions.add(permission)
        with tmp_to_org(cls.org):
            cls.org_manager.org_roles.add(org_role)
        Application = get_application_model()
        cls.application = Application.objects.create(
            name='Agent desktop', client_id='agent-desktop', client_type='public',
            authorization_grant_type='authorization-code', registration_source='dcr',
            redirect_uris='http://127.0.0.1/callback',
        )
        cls.registration = AgentApplication.objects.create(
            application=cls.application, resource='http://localhost:5000/koko/mcp',
        )
        cls.other = Application.objects.create(
            name='Other OAuth application', client_id='other-client', client_type='public',
            authorization_grant_type='authorization-code',
        )

    def setUp(self):
        self.enterContext(tmp_to_org(self.org))
        self.factory = APIRequestFactory()

    def request(self, method, path, user=None, data=None):
        request = getattr(self.factory, method)(
            path, data=data, format='json', HTTP_X_JMS_ORG=Organization.SYSTEM_ID,
            REMOTE_ADDR='192.0.2.10',
        )
        if user:
            force_authenticate(request, user=user)
        match = resolve(urlsplit(path).path)
        with transaction.atomic():
            return match.func(request, **match.kwargs)

    def test_only_platform_permission_allows_management_and_metadata(self):
        for user in (None, self.user, self.org_manager):
            for method, path in (
                ('get', self.url), ('options', self.url),
                ('post', f'{self.url}{self.registration.pk}/disable/'),
                ('post', f'{self.url}{self.registration.pk}/enable/'), ('post', self.url + 'cleanup/'),
                ('delete', f'{self.url}{self.registration.pk}/'),
            ):
                with self.subTest(user=user, method=method, path=path):
                    self.assertIn(self.request(method, path, user).status_code, (401, 403))
        response = self.request('options', self.url, self.manager)
        self.assertEqual(response.status_code, 200)
        self.assertIn('client_id', response.data['actions']['GET'])
        self.assertEqual(response.data['filters']['is_active']['type'], 'boolean')
        response = self.request('get', self.url + '?limit=10&search=desktop&is_active=true', self.manager)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(set(response.data['results'][0]), {
            'id', 'name', 'client_id', 'is_active', 'created', 'date_authorized',
        })
        self.assertEqual(response.data['results'][0]['client_id'], self.application.client_id)
        for terms, count in (('Agent,desktop', 1), ('Agent,missing', 0)):
            response = self.request('get', self.url + '?limit=10&search__icontains_all=' + terms, self.manager)
            self.assertEqual(response.data['count'], count)
        for method in ('post', 'patch'):
            path = self.url if method == 'post' else f'{self.url}{self.registration.pk}/'
            self.assertEqual(self.request(method, path, self.manager).status_code, 405)

    def test_delete_unused_client_preserves_other_applications(self):
        response = self.request('delete', f'{self.url}{self.registration.pk}/', self.manager)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(get_application_model().objects.filter(pk=self.application.pk).exists())
        self.assertFalse(AgentApplication.objects.filter(pk=self.registration.pk).exists())
        self.assertEqual(self.request('delete', f'{self.url}{self.registration.pk}/', self.manager).status_code, 404)
        self.assertEqual(self.request('post', f'{self.url}{self.registration.pk}/enable/', self.manager).status_code, 404)
        self.assertTrue(get_application_model().objects.filter(pk=self.other.pk).exists())

    def test_delete_revokes_grants_and_preserves_audit_in_other_org(self):
        expires = timezone.now() + timedelta(minutes=5)
        access = get_access_token_model().objects.create(
            user=self.user, application=self.application, token='deleted-agent-access', scope='agent:access',
            expires=expires,
        )
        refresh = get_refresh_token_model().objects.create(
            user=self.user, application=self.application, access_token=access, token='deleted-agent-refresh',
            token_family=uuid.uuid4(),
        )
        get_grant_model().objects.create(
            user=self.user, application=self.application, code='deleted-agent-code', expires=expires,
            redirect_uri='http://127.0.0.1/callback', scope='agent:access',
        )
        AgentOAuthBinding.objects.create(
            user=self.user, application=self.application, org_id=self.org.pk, refresh_family=refresh.token_family,
        )
        with tmp_to_org(Organization.DEFAULT_ID):
            session = AgentSession.objects.create(
                user=self.user, application=self.application, terminal=Terminal.objects.create(name='deleted-client-node'),
                oauth_token=access, resource=self.registration.resource, idempotency_key='client-delete-session',
                request_hash='0' * 64, date_expires=expires,
            )
            action = AgentAction.objects.create(
                session=session, user=self.user, application=self.application, kind='execute_command',
                idempotency_key='client-delete-action', request_hash='1' * 64, status='succeeded',
            )
            event = AgentEvent.objects.create(
                event_id=uuid.uuid4(), action=action, sequence=1, state='succeeded', payload_hash='2' * 64,
            )
        response = self.request('delete', f'{self.url}{self.registration.pk}/', self.manager)
        self.assertEqual(response.status_code, 204)
        for model in (get_access_token_model(), get_refresh_token_model(), get_grant_model(), AgentOAuthBinding):
            self.assertFalse(model.objects.filter(application=self.application).exists())
        self.assertFalse(AgentApplication.objects.filter(pk=self.registration.pk).exists())
        self.application.refresh_from_db()
        self.assertEqual(self.request('post', f'{self.url}{self.registration.pk}/enable/', self.manager).status_code, 404)
        self.assertEqual(self.application.redirect_uris, '')
        self.assertEqual(self.application.client_id, 'agent-desktop')
        with tmp_to_root_org():
            session.refresh_from_db()
            self.assertIsNone(session.oauth_token_id)
            self.assertEqual(AgentAction.objects.get(pk=action.pk).application_id, self.application.pk)
            self.assertEqual(AgentEvent.objects.get(pk=event.pk).payload_hash, '2' * 64)
            log = OperateLog.objects.get(resource_id=str(self.registration.pk), resource_type='Agent MCP client')
            self.assertEqual(str(log.org_id), Organization.SYSTEM_ID)
            self.assertEqual(log.user, str(self.manager))
        # A refresh/code request may have validated before deletion took the lock.
        request = OAuthRequest('http://localhost/token')
        request.client = self.application
        request.scopes = ['agent:access']
        with self.assertRaises(InvalidGrantError):
            AgentOAuth2Validator().save_bearer_token({'scope': 'agent:access'}, request)
        with self.assertRaises(InvalidScopeError):
            AgentOAuth2Validator().save_authorization_code(self.application.client_id, {'code': 'late-code'}, request)
        self.assertEqual(self.request('get', self.url + '?limit=10', self.manager).data['count'], 0)
        self.assertTrue(get_application_model().objects.filter(pk=self.other.pk).exists())

    def test_delete_rolls_back_if_operation_audit_fails(self):
        token = get_access_token_model().objects.create(
            user=self.user, application=self.application, token='delete-rollback-access',
            scope='agent:access', expires=timezone.now() + timedelta(minutes=5),
        )
        with patch('authentication.api.agent_client.record_client_operation', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                self.request('delete', f'{self.url}{self.registration.pk}/', self.manager)
        self.assertTrue(AgentApplication.objects.get(pk=self.registration.pk).is_active)
        self.assertTrue(get_access_token_model().objects.filter(pk=token.pk).exists())

    def test_disable_preserves_authority_records_and_audits_platform_actor(self):
        token = get_access_token_model().objects.create(
            user=self.user, application=self.application, token='agent-client-retained-token',
            scope='agent:access', expires=timezone.now() + timedelta(minutes=5),
        )
        for _ in range(2):
            response = self.request('post', f'{self.url}{self.registration.pk}/disable/', self.manager)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.data['is_active'])
        self.assertTrue(get_access_token_model().objects.filter(pk=token.pk).exists())
        self.assertTrue(get_application_model().objects.filter(pk=self.other.pk).exists())
        response = self.request('get', self.url + '?limit=10&is_active=false', self.manager)
        self.assertEqual(response.data['count'], 1)
        with tmp_to_root_org():
            logs = OperateLog.objects.filter(
                resource_id=str(self.registration.pk), resource_type='Agent MCP client',
            )
            self.assertEqual(logs.count(), 2)
            for log in logs:
                self.assertEqual(log.user, str(self.manager))
                self.assertEqual(str(log.org_id), Organization.SYSTEM_ID)
                self.assertEqual(log.remote_addr, '192.0.2.10')
                self.assertIn(self.application.client_id, log.diff['Client ID'])
                self.assertIn('disabled', log.diff['Result'])
        self.assertEqual(self.request('post', self.url + '99999999/disable/', self.manager).status_code, 404)

    def test_enable_restores_access_and_preserves_identity_authorizations_and_history(self):
        self.org.add_member(self.user)
        authorized_at = timezone.now() - timedelta(hours=1)
        AgentApplication.objects.filter(pk=self.registration.pk).update(date_authorized=authorized_at)
        token = get_access_token_model().objects.create(
            user=self.user, application=self.application, token='reenabled-agent-access',
            scope='agent:access', resource=[self.registration.resource],
            expires=timezone.now() + timedelta(minutes=5),
        )
        refresh = get_refresh_token_model().objects.create(
            user=self.user, application=self.application, access_token=token,
            token='reenabled-agent-refresh', token_family=uuid.uuid4(), resource=[self.registration.resource],
        )
        binding = AgentOAuthBinding.objects.create(
            user=self.user, application=self.application, org_id=self.org.pk, access_token=token,
        )
        node = Terminal.objects.create(name='reenabled-client-node', type='koko')
        with tmp_to_org(Organization.DEFAULT_ID):
            session = AgentSession.objects.create(
                user=self.user, application=self.application, terminal=node, oauth_token=token,
                resource=self.registration.resource, idempotency_key='reenabled-client-session',
                request_hash='0' * 64, date_expires=token.expires,
            )
            action = AgentAction.objects.create(
                session=session, user=self.user, application=self.application, kind='execute_command',
                idempotency_key='reenabled-client-action', request_hash='1' * 64, status='succeeded',
            )
            event = AgentEvent.objects.create(
                event_id=uuid.uuid4(), action=action, sequence=1, state='succeeded',
                payload={'data': 'retained output'}, payload_hash='2' * 64,
            )
        data = {'access_token': 'reenabled-agent-access', 'resource': self.registration.resource}
        self.assertEqual(self.request('post', f'{self.url}{self.registration.pk}/disable/', self.manager).status_code, 200)
        with self.assertRaises(PermissionDenied):
            agent_service.introspect(node, data)
        for user in (None, self.user, self.org_manager):
            self.assertIn(self.request('post', f'{self.url}{self.registration.pk}/enable/', user).status_code, (401, 403))
        self.assertFalse(AgentApplication.objects.get(pk=self.registration.pk).is_active)
        for _ in range(2):
            response = self.request('post', f'{self.url}{self.registration.pk}/enable/', self.manager)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data['is_active'])
            self.assertEqual(response.data['client_id'], self.application.client_id)
            self.assertEqual(response.data['id'], self.registration.pk)
        self.registration.refresh_from_db()
        self.application.refresh_from_db()
        token.refresh_from_db()
        refresh.refresh_from_db()
        binding.refresh_from_db()
        self.assertEqual(self.registration.date_authorized, authorized_at)
        self.assertEqual(self.application.redirect_uris, 'http://127.0.0.1/callback')
        self.assertEqual(token.token, 'reenabled-agent-access')
        self.assertEqual(refresh.token, 'reenabled-agent-refresh')
        self.assertIsNone(refresh.revoked)
        self.assertEqual(binding.org_id, self.org.pk)
        self.assertEqual(agent_service.introspect(node, data)['org_id'], str(self.org.pk))
        with tmp_to_root_org():
            session.refresh_from_db()
            action.refresh_from_db()
            event.refresh_from_db()
            self.assertEqual(session.oauth_token_id, token.pk)
            self.assertEqual(action.application_id, self.application.pk)
            self.assertEqual((event.payload, event.payload_hash), ({'data': 'retained output'}, '2' * 64))
            logs = OperateLog.objects.filter(resource_id=str(self.registration.pk), resource_type='Agent MCP client')
            self.assertEqual(logs.count(), 3)
            results = [log.diff['Result'] for log in logs]
            self.assertTrue(any('already enabled' in result for result in results))
            for log in logs:
                self.assertEqual(log.user, str(self.manager))
                self.assertEqual(str(log.org_id), Organization.SYSTEM_ID)
                self.assertIn(self.application.client_id, log.diff['Client ID'])
        self.assertTrue(get_application_model().objects.filter(pk=self.other.pk).exists())

    def test_enable_does_not_restore_expired_or_revoked_authorizations(self):
        self.org.add_member(self.user)
        token = get_access_token_model().objects.create(
            user=self.user, application=self.application, token='expired-agent-access',
            scope='agent:access', resource=[self.registration.resource],
            expires=timezone.now() - timedelta(minutes=1),
        )
        AgentApplication.objects.filter(pk=self.registration.pk).update(is_active=False)
        response = self.request('post', f'{self.url}{self.registration.pk}/enable/', self.manager)
        self.assertEqual(response.status_code, 200)
        token.refresh_from_db()
        self.assertLess(token.expires, timezone.now())
        node = Terminal.objects.create(name='expired-client-node', type='koko')
        with self.assertRaises(PermissionDenied):
            agent_service.introspect(node, {'access_token': token.token, 'resource': self.registration.resource})
        token.delete()
        self.assertEqual(self.request('post', f'{self.url}{self.registration.pk}/enable/', self.manager).status_code, 200)
        self.assertFalse(get_access_token_model().objects.filter(application=self.application).exists())

    def test_state_change_rolls_back_if_operation_audit_fails(self):
        for action, initial in (('enable', False), ('disable', True)):
            AgentApplication.objects.filter(pk=self.registration.pk).update(is_active=initial)
            with patch('authentication.api.agent_client.record_client_operation', side_effect=RuntimeError('audit unavailable')):
                with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                    self.request('post', f'{self.url}{self.registration.pk}/{action}/', self.manager)
            self.assertEqual(AgentApplication.objects.get(pk=self.registration.pk).is_active, initial)

    def test_cleanup_returns_bounded_result_and_records_deleted_client(self):
        get_application_model().objects.filter(pk=self.application.pk).update(
            created=timezone.now() - timedelta(days=8),
        )
        response = self.request('post', self.url + 'cleanup/', self.manager)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'scanned': 1, 'deleted': 1, 'skipped': 0})
        self.assertFalse(AgentApplication.objects.filter(pk=self.registration.pk).exists())
        self.assertTrue(get_application_model().objects.filter(pk=self.other.pk).exists())
        with tmp_to_root_org():
            log = OperateLog.objects.get(resource_id=str(self.registration.pk), resource_type='Agent MCP client')
            self.assertEqual(log.user, str(self.manager))
            self.assertEqual(str(log.org_id), Organization.SYSTEM_ID)
            self.assertIn(self.application.client_id, log.diff['Client ID'])

    def test_cleanup_reports_coordination_failure(self):
        for error, code in ((AgentClientCleanupBusy(), 409), (AgentClientCleanupUnavailable(), 503)):
            with self.subTest(code=code), patch(
                'authentication.api.agent_client.cleanup_agent_oauth_clients', side_effect=error,
            ):
                self.assertEqual(self.request('post', self.url + 'cleanup/', self.manager).status_code, code)
        self.assertTrue(AgentApplication.objects.filter(pk=self.registration.pk).exists())

    def test_periodic_oauth_cleanup_reuses_client_maintenance(self):
        from authentication.tasks import clear_oauth2_provider_expired_tokens
        with patch('oauth2_provider.models.clear_expired') as tokens, patch(
            'authentication.services.agent_clients.cleanup_agent_oauth_clients',
            return_value={'scanned': 0, 'deleted': 0, 'skipped': 0},
        ) as clients:
            clear_oauth2_provider_expired_tokens()
            tokens.assert_called_once_with()
            clients.assert_called_once_with()
