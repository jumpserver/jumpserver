from unittest.mock import patch

from django.test import TestCase
from oauth2_provider.models import get_application_model
from rest_framework.test import APIClient

from orgs.models import Organization
from terminal.models import AgentApplication
from users.models import User


class AgentClientPrivacyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create(username='agent-client-system-admin')
        cls.admin.system_roles.add_role_system_admin()
        cls.owner = User.objects.create(username='agent-client-owner')
        cls.application = get_application_model().objects.create(
            name='Private Agent', client_id='private-agent', client_type='public',
            authorization_grant_type='authorization-code', redirect_uris='http://127.0.0.1/callback',
        )
        cls.registration = AgentApplication.objects.create(
            application=cls.application, resource='https://jumpserver.example/koko/mcp',
        )

    def test_admin_client_endpoints_are_unavailable_even_to_system_admin(self):
        client = APIClient()
        client.force_authenticate(self.admin)
        base = '/api/v1/authentication/'
        paths = (
            'agent-clients/', f'agent-clients/{self.registration.pk}/',
            f'agent-clients/{self.registration.pk}/disable/', f'agent-clients/{self.registration.pk}/enable/',
            'agent-clients/cleanup/', f'agent-client-authorizations/?user_id={self.owner.pk}',
            f'agent-client-authorizations/{self.application.pk}/?user_id={self.owner.pk}',
        )
        for path in paths:
            for method in ('get', 'options', 'post', 'delete'):
                with self.subTest(path=path, method=method):
                    response = getattr(client, method)(base + path, HTTP_X_JMS_ORG=Organization.DEFAULT_ID)
                    self.assertEqual(response.status_code, 404)
        self.assertTrue(AgentApplication.objects.get(pk=self.registration.pk).is_active)

    def test_periodic_oauth_cleanup_reuses_client_maintenance(self):
        from authentication.tasks import clear_oauth2_provider_expired_tokens
        with patch('oauth2_provider.models.clear_expired') as tokens, patch(
            'authentication.services.agent_clients.cleanup_agent_oauth_clients',
            return_value={'scanned': 0, 'deleted': 0, 'skipped': 0},
        ) as clients:
            clear_oauth2_provider_expired_tokens()
            tokens.assert_called_once_with()
            clients.assert_called_once_with()
