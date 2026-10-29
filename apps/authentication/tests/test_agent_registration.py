import json
import time
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone
from oauth2_provider.models import get_access_token_model, get_application_model
from oauth2_provider.settings import oauth2_settings
from redis.exceptions import RedisError

from authentication.backends.oauth2_provider import agent_registration as registration
from authentication.backends.oauth2_provider.agent import AgentAuthorizationServerView
from authentication.services import agent_clients
from common.utils.lock import DistributedLock
from terminal.models import AgentApplication
from users.models import User


@override_settings(MCP_ENABLED=True, MCP_DCR_ENABLED=True, MCP_PUBLIC_URL='https://jumpserver.example/koko/mcp')
class AgentClientRegistrationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.Application = get_application_model()
        self.url = reverse('authentication:oauth2-provider:agent-register')
        self.view = registration.AgentClientRegistrationView.as_view()
        self.metadata = {
            'client_name': 'MCP test client',
            'redirect_uris': ['http://127.0.0.1/callback/client', 'http://[::1]/callback/client?channel=pc'],
            'token_endpoint_auth_method': 'none',
            'grant_types': ['authorization_code', 'refresh_token'],
            'response_types': ['code'],
        }
        window = int(time.time()) // 60
        cache.delete_many([f'agent-dcr-rate:{window}', f'agent-dcr-rate:{window + 1}'])

    def register(self, **metadata):
        request = self.factory.post(self.url, json.dumps({**self.metadata, **metadata}),
                                    content_type='application/json', HTTP_HOST='untrusted.example')
        return self.view(request)

    def application(self, **metadata):
        response = self.register(**metadata)
        self.assertEqual(response.status_code, 201, response.content)
        return self.Application.objects.get(client_id=json.loads(response.content)['client_id'])

    def test_registration_is_public_resource_bound_and_does_not_grant_access(self):
        schemes = list(oauth2_settings.ALLOWED_REDIRECT_URI_SCHEMES)
        response = self.register(client_id='supplied-id', client_secret='supplied-secret',
                                 resource='https://untrusted.example/mcp', skip_authorization=True)
        self.assertEqual(response.status_code, 201, response.content)
        data = json.loads(response.content)
        app = self.Application.objects.get(client_id=data['client_id'])
        self.assertNotEqual(app.client_id, 'supplied-id')
        self.assertEqual(app.client_type, app.CLIENT_PUBLIC)
        self.assertEqual(app.client_secret, '')
        self.assertFalse(app.skip_authorization)
        self.assertEqual(app.agent_registration.resource, 'https://jumpserver.example/koko/mcp')
        self.assertTrue(app.agent_registration.is_active)
        self.assertIsNone(app.agent_registration.date_authorized)
        self.assertEqual(app.registration_source, app.RegistrationSource.DCR)
        self.assertTrue(app.redirect_uri_allowed('http://127.0.0.1:49152/callback/client'))
        self.assertTrue(app.redirect_uri_allowed('http://[::1]:49152/callback/client?channel=pc'))
        self.assertFalse(app.redirect_uri_allowed('http://127.0.0.1:49152/other'))
        self.assertEqual(list(oauth2_settings.ALLOWED_REDIRECT_URI_SCHEMES), schemes)
        self.assertEqual(get_access_token_model().objects.filter(application=app).count(), 0)
        self.assertTrue({'client_secret', 'registration_access_token', 'registration_client_uri'}.isdisjoint(data))
        self.assertEqual(data['scope'], 'agent:access')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertNotEqual(self.application().pk, app.pk)
        self.assertIn('default', resolve(self.url).func._non_atomic_requests)

    def test_discovery_and_registration_share_explicit_deployment_enablement(self):
        metadata = AgentAuthorizationServerView().get_metadata(self.factory.get('/metadata', secure=True))
        self.assertTrue(metadata['registration_endpoint'].endswith(self.url))
        with override_settings(MCP_DCR_ENABLED=False):
            self.assertEqual(self.register().status_code, 404)
            self.assertNotIn('registration_endpoint', AgentAuthorizationServerView().get_metadata(self.factory.get('/metadata')))
        with override_settings(MCP_ENABLED=False):
            self.assertEqual(self.register().status_code, 404)
            self.assertNotIn('registration_endpoint', AgentAuthorizationServerView().get_metadata(self.factory.get('/metadata')))
        for resource in ('', 'https://host/mcp/', 'https://user@host/mcp', 'https://host/mcp?', 'https://host/mcp#'):
            with self.subTest(resource=resource), override_settings(MCP_PUBLIC_URL=resource):
                with self.assertRaises(ImproperlyConfigured):
                    registration.configured_resource()
        with override_settings(MCP_PUBLIC_URL='http://internal.example/koko/mcp'):
            self.assertEqual(self.application().agent_registration.resource, 'http://internal.example/koko/mcp')

    def test_invalid_registration_never_creates_an_application(self):
        before = self.Application.objects.count()
        for uri in ('https://remote.example/callback', 'http://remote.example/callback',
                    'http://localhost/callback', 'http://127.0.0.1.evil/callback',
                    'http://user@127.0.0.1/callback', 'http://127.0.0.1/callback#fragment',
                    'http://127.0.0.1:0/callback', 'http://127.0.0.1/call\nback'):
            with self.subTest(uri=uri):
                self.assertEqual(self.register(redirect_uris=[uri]).status_code, 400)
        for invalid in ({'grant_types': ['client_credentials']}, {'scope': 'read'},
                        {'token_endpoint_auth_method': 'client_secret_basic'}, {'response_types': ['token']},
                        {'client_name': 'JumpServer Client'}, {'redirect_uris': []},
                        {'redirect_uris': self.metadata['redirect_uris'] * 3}, {'client_name': 'x' * 129}):
            with self.subTest(metadata=invalid):
                self.assertEqual(self.register(**invalid).status_code, 400)
        request = self.factory.post(self.url, b'{' + b' ' * registration.MAX_BODY_BYTES, content_type='application/json')
        self.assertEqual(self.view(request).status_code, 413)
        request = self.factory.post(self.url, b'\xff', content_type='application/json')
        self.assertEqual(self.view(request).status_code, 400)
        request = self.factory.post(self.url, b'[' * 2000 + b']' * 2000, content_type='application/json')
        self.assertEqual(self.view(request).status_code, 400)
        self.assertEqual(self.Application.objects.count(), before)

    def test_disabling_during_registration_does_not_create_a_client(self):
        before = self.Application.objects.count()
        request = self.factory.post(self.url, json.dumps(self.metadata), content_type='application/json')
        read = request.read

        def read_and_disable(size):
            settings.MCP_ENABLED = False
            return read(size)

        with override_settings(MCP_ENABLED=True), patch.object(request, 'read', side_effect=read_and_disable):
            response = self.view(request)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.Application.objects.count(), before)

    def test_rate_capacity_and_coordination_fail_closed(self):
        before = self.Application.objects.count()
        with patch.object(registration, 'MAX_CLIENTS', 0):
            self.assertEqual(self.register().status_code, 429)
        lock = DistributedLock(registration.REGISTRATION_LOCK, expire=5)
        self.assertTrue(lock.acquire(blocking=False))
        try:
            self.assertEqual(self.register().status_code, 429)
        finally:
            lock.release()
        with patch.object(registration.cache, 'add', side_effect=RedisError):
            self.assertEqual(self.register().status_code, 503)
        with patch.object(registration, 'REGISTRATIONS_PER_MINUTE', 0):
            response = self.register()
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response['Retry-After'], '60')
        self.assertEqual(self.Application.objects.count(), before)

    def test_cleanup_retains_authorized_referenced_other_and_recent_clients(self):
        unused, authorized, referenced, other, recent = [self.application() for _ in range(5)]
        old = timezone.now() - timedelta(days=8)
        self.Application.objects.exclude(pk=recent.pk).filter(
            pk__in=[unused.pk, authorized.pk, referenced.pk, other.pk],
        ).update(created=old)
        AgentApplication.objects.filter(application=authorized).update(date_authorized=timezone.now())
        AgentApplication.objects.filter(application=other).delete()
        self.Application.objects.filter(pk=other.pk).update(registration_source=self.Application.RegistrationSource.MANUAL)
        get_access_token_model().objects.create(
            application=referenced, user=User.objects.create(username='dcr-token-user'),
            token='dcr-cleanup-test', scope='agent:access', expires=timezone.now() + timedelta(minutes=5),
        )
        registration_id = unused.agent_registration.pk
        deleted = []
        result = agent_clients.cleanup_agent_oauth_clients(on_delete=deleted.append)
        self.assertEqual(result, {'scanned': 1, 'deleted': 1, 'skipped': 0})
        self.assertEqual(deleted, [{'id': registration_id, 'client_id': unused.client_id, 'name': unused.name}])
        self.assertFalse(self.Application.objects.filter(pk=unused.pk).exists())
        self.assertEqual(self.Application.objects.filter(pk__in=[authorized.pk, referenced.pk, other.pk, recent.pk]).count(), 4)

    def test_cleanup_batch_skips_old_references_before_limiting(self):
        referenced, first, second = [self.application() for _ in range(3)]
        self.Application.objects.filter(pk=referenced.pk).update(created=timezone.now() - timedelta(days=10))
        self.Application.objects.filter(pk__in=[first.pk, second.pk]).update(created=timezone.now() - timedelta(days=8))
        get_access_token_model().objects.create(
            application=referenced, user=User.objects.create(username='cleanup-limit-user'),
            token='dcr-cleanup-limited', scope='agent:access', expires=timezone.now() + timedelta(minutes=5),
        )
        for _ in range(2):
            self.assertEqual(agent_clients.cleanup_agent_oauth_clients(limit=1),
                             {'scanned': 1, 'deleted': 1, 'skipped': 0})
        self.assertTrue(self.Application.objects.filter(pk=referenced.pk).exists())
        self.assertFalse(self.Application.objects.filter(pk__in=[first.pk, second.pk]).exists())

    def test_cleanup_coordination_validation_and_callback_rollback(self):
        unused = self.application()
        self.Application.objects.filter(pk=unused.pk).update(created=timezone.now() - timedelta(days=8))
        for kwargs in ({'limit': 0}, {'limit': 1001}, {'limit': True}, {'older_than_days': 0}, {'older_than_days': 3651}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                agent_clients.cleanup_agent_oauth_clients(**kwargs)
        lock = DistributedLock(registration.REGISTRATION_LOCK, expire=5)
        self.assertTrue(lock.acquire(blocking=False))
        try:
            with self.assertRaises(agent_clients.AgentClientCleanupBusy):
                agent_clients.cleanup_agent_oauth_clients()
        finally:
            lock.release()
        with patch.object(agent_clients, 'DistributedLock', side_effect=RedisError):
            with self.assertRaises(agent_clients.AgentClientCleanupUnavailable):
                agent_clients.cleanup_agent_oauth_clients()

        def reject_audit(client):
            self.assertEqual(client['client_id'], unused.client_id)
            raise RuntimeError('audit unavailable')

        with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
            agent_clients.cleanup_agent_oauth_clients(on_delete=reject_audit)
        self.assertTrue(self.Application.objects.filter(pk=unused.pk).exists())
