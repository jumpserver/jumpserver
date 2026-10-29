from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit

from django.db import transaction
from django.test import TestCase
from django.urls import resolve
from django.utils import timezone
from oauth2_provider.models import get_application_model, get_access_token_model
from rest_framework.test import APIRequestFactory, force_authenticate

from audits.models import OperateLog
from authentication.services.agent_clients import AgentClientCleanupBusy, AgentClientCleanupUnavailable
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from rbac.models import Permission, Role
from terminal.models import AgentApplication
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
                ('post', f'{self.url}{self.registration.pk}/disable/'), ('post', self.url + 'cleanup/'),
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
        for method in ('post', 'patch', 'delete'):
            path = self.url if method == 'post' else f'{self.url}{self.registration.pk}/'
            self.assertEqual(self.request(method, path, self.manager).status_code, 405)

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
