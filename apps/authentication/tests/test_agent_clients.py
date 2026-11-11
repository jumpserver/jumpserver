import uuid
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import Resolver404, resolve
from django.utils import timezone
from oauth2_provider.models import get_access_token_model, get_application_model, get_grant_model, get_refresh_token_model

from authentication.services.agent_clients import agent_oauth_bindings, cleanup_agent_oauth_bindings
from orgs.models import Organization
from terminal.models import AgentApplication, AgentOAuthBinding, AgentSession, Terminal
from users.models import User


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
            'authentication.services.agent_clients.cleanup_agent_oauth_bindings',
            return_value={'scanned': 0, 'deleted': 0},
        ) as bindings, patch(
            'authentication.services.agent_clients.cleanup_agent_oauth_clients',
            return_value={'scanned': 0, 'deleted': 0, 'skipped': 0},
        ) as clients:
            clear_oauth2_provider_expired_tokens()
            logins.assert_called_once_with()
            tokens.assert_called_once_with()
            bindings.assert_called_once_with()
            clients.assert_called_once_with()


class AgentOAuthBindingCleanupTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='binding-cleanup-user')
        cls.application = get_application_model().objects.create(name='Binding cleanup client')
        AgentApplication.objects.create(application=cls.application, resource='https://jumpserver.example/koko/mcp')

    def access_binding(self, seconds, *, refresh=False, revoked=False):
        access = get_access_token_model().objects.create(
            user=self.user, application=self.application, token=uuid.uuid4().hex,
            scope='agent:access', expires=timezone.now() + timedelta(seconds=seconds),
        )
        binding = AgentOAuthBinding.objects.create(user=self.user, application=self.application, access_token=access)
        family = None
        if refresh:
            token = get_refresh_token_model().objects.create(
                user=self.user, application=self.application, access_token=access, token=uuid.uuid4().hex,
                token_family=uuid.uuid4(), revoked=timezone.now() if revoked else None,
            )
            family = AgentOAuthBinding.objects.create(
                user=self.user, application=self.application, refresh_family=token.token_family,
            )
        return binding, family

    def test_cleanup_obeys_credential_lifetimes_and_keeps_valid_subjects(self):
        with self.settings(OAUTH2_PROVIDER={**settings.OAUTH2_PROVIDER, 'REFRESH_TOKEN_EXPIRE_SECONDS': 60}):
            standalone, _ = self.access_binding(120)
            expired_access, active_family = self.access_binding(-30, refresh=True)
            self.access_binding(-120, refresh=True)
            self.access_binding(120, refresh=True, revoked=True)
            orphan = get_refresh_token_model().objects.create(
                user=self.user, application=self.application, token=uuid.uuid4().hex, token_family=uuid.uuid4(),
            )
            AgentOAuthBinding.objects.create(user=self.user, application=self.application, refresh_family=orphan.token_family)
            # A revoked rotation predecessor must not invalidate its live successor.
            get_refresh_token_model().objects.create(
                user=self.user, application=self.application, token=uuid.uuid4().hex,
                token_family=active_family.refresh_family, revoked=timezone.now(),
            )
            grant = get_grant_model().objects.create(
                user=self.user, application=self.application, code=uuid.uuid4().hex,
                redirect_uri='http://127.0.0.1/callback', expires=timezone.now() + timedelta(minutes=1),
            )
            grant_binding = AgentOAuthBinding.objects.create(user=self.user, application=self.application, grant=grant)
            expected = {standalone.pk, active_family.pk, grant_binding.pk}
            self.assertEqual(set(agent_oauth_bindings().filter(is_live=True).values_list('pk', flat=True)), expected)
            cleanup_agent_oauth_bindings()
            self.assertEqual(set(AgentOAuthBinding.objects.values_list('pk', flat=True)), expected)
            self.assertTrue(get_access_token_model().objects.filter(pk=expired_access.access_token_id).exists())
            self.assertTrue(get_refresh_token_model().objects.filter(pk=orphan.pk).exists())
            self.assertEqual(cleanup_agent_oauth_bindings(), {'scanned': 0, 'deleted': 0})

    def test_cleanup_is_bounded_keeps_last_expired_entry_and_preserves_audit(self):
        session = AgentSession.objects.create(
            user=self.user, application=self.application, terminal=Terminal.objects.create(name='binding-cleanup-node'),
            org_id=Organization.DEFAULT_ID,
            resource=self.application.agent_registration.resource, idempotency_key='retained-history',
            request_hash='0' * 64, date_expires=timezone.now() - timedelta(minutes=1),
        )
        bindings = [AgentOAuthBinding.objects.create(
            user=self.user, application=self.application, refresh_family=uuid.uuid4(),
        ) for _ in range(3)]
        other_application = get_application_model().objects.create(name='Another expired client')
        other_binding = AgentOAuthBinding.objects.create(
            user=self.user, application=other_application, refresh_family=uuid.uuid4(),
        )
        for _ in range(2):
            self.assertEqual(cleanup_agent_oauth_bindings(limit=1), {'scanned': 1, 'deleted': 1})
        self.assertEqual(set(AgentOAuthBinding.objects.values_list('pk', flat=True)), {bindings[-1].pk, other_binding.pk})
        self.assertFalse(agent_oauth_bindings().get(pk=bindings[-1].pk).is_live)
        self.assertEqual(cleanup_agent_oauth_bindings(), {'scanned': 0, 'deleted': 0})
        session.refresh_from_db()
        self.assertEqual((session.user_id, session.application_id), (self.user.pk, self.application.pk))

    def test_cleanup_validates_batch_limit(self):
        for limit in (True, 0, 1001):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                cleanup_agent_oauth_bindings(limit=limit)
