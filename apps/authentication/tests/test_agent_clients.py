from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import Resolver404, resolve


class AgentClientPrivacyTests(SimpleTestCase):
    def test_removed_admin_client_routes_are_not_registered(self):
        base = '/api/v1/authentication/'
        paths = (
            'agent-clients/', 'agent-clients/1/',
            'agent-clients/1/disable/', 'agent-clients/1/enable/',
            'agent-clients/cleanup/', 'agent-client-authorizations/',
            'agent-client-authorizations/1/',
        )
        for path in paths:
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolve(base + path)

    def test_periodic_oauth_cleanup_reuses_client_maintenance(self):
        from authentication.tasks import clear_oauth2_provider_expired_tokens
        with patch('authentication.services.client_login_session.clear_client_login_sessions') as logins, patch(
            'oauth2_provider.models.clear_expired',
        ) as tokens, patch(
            'authentication.services.agent_clients.cleanup_agent_oauth_clients',
            return_value={'scanned': 0, 'deleted': 0, 'skipped': 0},
        ) as clients:
            clear_oauth2_provider_expired_tokens()
            logins.assert_called_once_with()
            tokens.assert_called_once_with()
            clients.assert_called_once_with()
