import base64
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from fnmatch import fnmatchcase
from io import StringIO
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import close_old_connections
from django.db.utils import OperationalError, ProgrammingError
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import include, path
from django.utils import timezone
from oauth2_provider.models import (
    get_access_token_model, get_application_model, get_refresh_token_model,
)
from oauth2_provider.oauth2_validators import OAuth2Validator
from oauth2_provider.views import AuthorizationView, RevokeTokenView, TokenView

from authentication.backends.oauth2_provider.utils import get_or_create_jumpserver_client_application
from authentication.backends.oauth2_provider.signal_handlers import on_django_ready_refresh_oauth2_provider_client
from authentication.management.commands.init_oauth2_provider import Command
from authentication.backends.oauth2_provider.views import OAuthAuthorizationServerView


LEGACY_CALLBACK = 'jms://auth/callback'
CLIENT_CALLBACK = 'jms2://auth/callback'
DEV_CALLBACK = 'http://127.0.0.1:14876/auth/callback'

urlpatterns = [
    path('core/auth/', include(([
        path('oauth2-provider/', include((
            'authentication.backends.oauth2_provider.urls', 'oauth2-provider',
        ))),
    ], 'authentication'))),
]


@override_settings(
    OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME='JumpServer Client',
    OAUTH2_PROVIDER_CLIENT_REDIRECT_URI=CLIENT_CALLBACK,
)
class OAuthClientApplicationTests(TestCase):
    def setUp(self):
        self.Application = get_application_model()

    def create_application(self, **kwargs):
        return self.Application.objects.create(**{
            'name': 'JumpServer Client',
            'client_type': self.Application.CLIENT_PUBLIC,
            'authorization_grant_type': self.Application.GRANT_AUTHORIZATION_CODE,
            'redirect_uris': LEGACY_CALLBACK,
            **kwargs,
        })

    def test_new_client_allows_only_current_desktop_callback(self):
        application = get_or_create_jumpserver_client_application()

        application.clean()
        self.assertTrue(application.redirect_uri_allowed(CLIENT_CALLBACK))
        self.assertFalse(application.redirect_uri_allowed(LEGACY_CALLBACK))
        self.assertFalse(application.redirect_uri_allowed(DEV_CALLBACK))
        self.assertTrue(application.skip_authorization)

    def test_initialization_updates_only_callbacks_and_preserves_tokens(self):
        original_uris = f'{LEGACY_CALLBACK}\nhttps://custom.example/callback {DEV_CALLBACK}'
        application = self.create_application(redirect_uris=original_uris, skip_authorization=False)
        user = get_user_model().objects.create(username='oauth-client-test')
        access_token = get_access_token_model().objects.create(
            application=application, user=user, token='test-access-token',
            scope='read write', expires=timezone.now() + timedelta(hours=1),
        )
        get_refresh_token_model().objects.create(
            application=application, user=user, access_token=access_token, token='test-refresh-token',
        )
        other = self.create_application(name='Another OAuth application')
        before = self.Application.objects.filter(pk=application.pk).values().get()
        access_before = list(get_access_token_model().objects.values())
        refresh_before = list(get_refresh_token_model().objects.values())

        call_command(Command(), stdout=StringIO())

        after = self.Application.objects.filter(pk=application.pk).values().get()
        self.assertEqual(after.pop('redirect_uris').split(), original_uris.split()[1:] + [CLIENT_CALLBACK])
        before.pop('redirect_uris')
        self.assertEqual(after, before)
        self.assertEqual(list(get_access_token_model().objects.values()), access_before)
        self.assertEqual(list(get_refresh_token_model().objects.values()), refresh_before)
        self.assertEqual(self.Application.objects.count(), 2)
        other.refresh_from_db()
        self.assertEqual(other.redirect_uris, LEGACY_CALLBACK)

    def test_repeated_initialization_does_not_write_or_duplicate_callbacks(self):
        application = get_or_create_jumpserver_client_application()
        with self.assertNumQueries(3):  # Savepoint, locked read, release; no UPDATE.
            again = get_or_create_jumpserver_client_application()
        self.assertEqual(again.pk, application.pk)
        self.assertEqual(again.redirect_uris.split(), [CLIENT_CALLBACK])

    def test_duplicate_clients_do_not_break_startup_or_replace_credentials_and_tokens(self):
        first = self.create_application()
        duplicate = self.create_application(skip_authorization=False)
        other = self.create_application(name='Another OAuth application')
        before = list(self.Application.objects.order_by('pk').values())
        user = get_user_model().objects.create(username='duplicate-oauth-client-test')
        access_token = get_access_token_model().objects.create(
            application=duplicate, user=user, token='duplicate-client-access-token',
            scope='read', expires=timezone.now() + timedelta(hours=1),
        )
        get_refresh_token_model().objects.create(
            application=duplicate, user=user, access_token=access_token,
            token='duplicate-client-refresh-token',
        )
        access_before = list(get_access_token_model().objects.values())
        refresh_before = list(get_refresh_token_model().objects.values())

        with patch(
            'authentication.backends.oauth2_provider.signal_handlers.clear_oauth2_authorization_server_view_cache',
        ):
            on_django_ready_refresh_oauth2_provider_client(sender=None)
        call_command(Command(), stdout=StringIO())
        selected = get_or_create_jumpserver_client_application()

        self.assertEqual(selected.pk, first.pk)
        after = list(self.Application.objects.order_by('pk').values())
        self.assertEqual(len(after), len(before))
        for original, updated in zip(before, after):
            expected = LEGACY_CALLBACK if original['id'] == other.pk else CLIENT_CALLBACK
            self.assertEqual(updated.pop('redirect_uris'), expected)
            original.pop('redirect_uris')
            self.assertEqual(updated, original)
        self.assertEqual(list(get_access_token_model().objects.values()), access_before)
        self.assertEqual(list(get_refresh_token_model().objects.values()), refresh_before)

    @override_settings(
        OAUTH2_PROVIDER_CLIENT_REDIRECT_URI=f'{CLIENT_CALLBACK} {DEV_CALLBACK}',
    )
    def test_development_initialization_adds_loopback_to_existing_client(self):
        application = self.create_application()

        updated = get_or_create_jumpserver_client_application()

        self.assertEqual(updated.pk, application.pk)
        self.assertEqual(updated.redirect_uris.split(), [CLIENT_CALLBACK, DEV_CALLBACK])

    def test_callback_matching_remains_exact(self):
        application = get_or_create_jumpserver_client_application()

        for uri in (
            'jms2://other/callback', 'jms2://auth/callback/other',
            'https://attacker.example/callback', 'http://127.0.0.1:14876/other',
        ):
            with self.subTest(uri=uri):
                self.assertFalse(application.redirect_uri_allowed(uri))

    def test_startup_clears_metadata_before_refreshing_existing_client(self):
        application = self.create_application()

        def check_before_refresh():
            application.refresh_from_db()
            self.assertEqual(application.redirect_uris, LEGACY_CALLBACK)

        with patch(
            'authentication.backends.oauth2_provider.signal_handlers.clear_oauth2_authorization_server_view_cache',
            side_effect=check_before_refresh,
        ) as clear_cache:
            on_django_ready_refresh_oauth2_provider_client(sender=None)

        clear_cache.assert_called_once_with()
        application.refresh_from_db()
        self.assertEqual(application.redirect_uris.split(), [CLIENT_CALLBACK])
        self.assertEqual(self.Application.objects.count(), 1)

    def test_startup_clears_cache_even_before_database_is_available(self):
        for error in (OperationalError('unavailable'), ProgrammingError('missing table')):
            with self.subTest(error=type(error).__name__), patch(
                'authentication.backends.oauth2_provider.signal_handlers.clear_oauth2_authorization_server_view_cache',
            ) as clear_cache, patch(
                'authentication.backends.oauth2_provider.signal_handlers.get_or_create_jumpserver_client_application',
                side_effect=error,
            ):
                on_django_ready_refresh_oauth2_provider_client(sender=None)
                clear_cache.assert_called_once_with()

    def test_metadata_invalidation_covers_get_head_and_headers_only_for_oauth(self):
        from authentication.backends.oauth2_provider.utils import clear_oauth2_authorization_server_view_cache

        with patch('authentication.backends.oauth2_provider.utils.cache') as cache:
            clear_oauth2_authorization_server_view_cache()
        pattern = cache.delete_pattern.call_args.args[0]
        for key in (
            'views.decorators.cache.cache_page.oauth2_provider_metadata.GET.urlhash.headerhash.en-us.UTC',
            'views.decorators.cache.cache_page.oauth2_provider_metadata.HEAD.urlhash.headerhash.en-us.UTC',
            'views.decorators.cache.cache_header.oauth2_provider_metadata.urlhash.en-us.UTC',
        ):
            with self.subTest(key=key):
                self.assertTrue(fnmatchcase(key, pattern))
        self.assertFalse(fnmatchcase('views.decorators.cache.cache_page.other.GET.urlhash', pattern))


@override_settings(
    OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME='JumpServer Client',
    OAUTH2_PROVIDER_CLIENT_REDIRECT_URI=CLIENT_CALLBACK,
)
class OAuthClientConcurrentInitializationTests(TransactionTestCase):
    def test_concurrent_first_start_creates_one_client(self):
        barrier = Barrier(4)

        def initialize():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return get_or_create_jumpserver_client_application().pk
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=4) as executor:
            clients = list(executor.map(lambda _: initialize(), range(4)))

        self.assertEqual(len(set(clients)), 1)
        self.assertEqual(get_application_model().objects.count(), 1)

    def test_failed_creation_rolls_back_and_releases_initialization_lock(self):
        Application = get_application_model()
        original_save = Application.save

        def fail_after_insert(application, *args, **kwargs):
            original_save(application, *args, **kwargs)
            raise RuntimeError('Initialization failed after insert')

        with patch.object(Application, 'save', fail_after_insert):
            with self.assertRaisesMessage(RuntimeError, 'Initialization failed after insert'):
                get_or_create_jumpserver_client_application()

        self.assertFalse(Application.objects.exists())
        application = get_or_create_jumpserver_client_application()
        self.assertEqual(Application.objects.get().pk, application.pk)


@override_settings(
    ROOT_URLCONF=__name__,
    OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME='JumpServer Client',
    OAUTH2_PROVIDER_CLIENT_REDIRECT_URI=CLIENT_CALLBACK,
    OAUTH2_PROVIDER={
        'ALLOWED_REDIRECT_URI_SCHEMES': ['https', 'jms2'],
        'PKCE_REQUIRED': True,
        'ALWAYS_RELOAD_OAUTHLIB_CORE': True,
    },
)
class OAuthClientFlowCompatibilityTests(TestCase):
    def setUp(self):
        self.Application = get_application_model()
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create(username='oauth-flow-test')
        self.verifier = 'oauth-client-compatibility-test-verifier-0123456789'

    def authorize(self, application):
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self.verifier.encode()).digest(),
        ).rstrip(b'=').decode()
        request = self.factory.get('/core/auth/oauth2-provider/authorize/', {
            'client_id': application.client_id,
            'redirect_uri': CLIENT_CALLBACK,
            'response_type': 'code',
            'scope': 'read write',
            'state': 'oauth-compatibility-state',
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
        }, secure=True)
        request.user = self.user
        response = AuthorizationView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        callback = urlsplit(response['Location'])
        self.assertEqual(f'{callback.scheme}://{callback.netloc}{callback.path}', CLIENT_CALLBACK)
        params = parse_qs(callback.query)
        self.assertEqual(params['state'], ['oauth-compatibility-state'])
        return params['code'][0]

    def token_request(self, **data):
        request = self.factory.post('/core/auth/oauth2-provider/token/', data, secure=True)
        response = TokenView.as_view()(request)
        return response.status_code, json.loads(response.content)

    def exchange_code(self, application, code, verifier=None):
        return self.token_request(
            grant_type='authorization_code', client_id=application.client_id,
            code=code, redirect_uri=CLIENT_CALLBACK,
            code_verifier=self.verifier if verifier is None else verifier,
        )

    def discover(self):
        request = self.factory.get(
            '/core/auth/oauth2-provider/.well-known/oauth-authorization-server', secure=True,
        )
        return OAuthAuthorizationServerView().get_metadata(request)

    def create_duplicate_clients(self):
        first = get_or_create_jumpserver_client_application()
        duplicate = self.Application.objects.create(
            name=first.name, client_type=first.client_type,
            authorization_grant_type=first.authorization_grant_type,
            redirect_uris=CLIENT_CALLBACK, skip_authorization=True,
        )
        return first, duplicate

    def test_new_client_discovery_pkce_login_and_token_exchange(self):
        metadata = self.discover()
        application = self.Application.objects.get(client_id=metadata['client_id'])
        self.assertEqual(metadata['code_challenge_methods_supported'], ['S256'])
        code = self.authorize(application)
        status, tokens = self.exchange_code(application, code)
        self.assertEqual(status, 200, tokens)
        self.assertTrue(tokens['refresh_token'])
        self.assertTrue(OAuth2Validator().validate_bearer_token(
            tokens['access_token'], ['read', 'write'], SimpleNamespace(),
        ))

    def test_pending_codes_for_both_clients_survive_initialization(self):
        applications = self.create_duplicate_clients()
        codes = [self.authorize(application) for application in applications]

        # Discovery now selects the first client, but pending logins keep their original ID.
        self.assertEqual(self.discover()['client_id'], applications[0].client_id)
        for application, code in zip(applications, codes):
            with self.subTest(application=application.pk):
                status, tokens = self.exchange_code(application, code)
                self.assertEqual(status, 200, tokens)
                self.assertTrue(tokens['refresh_token'])

    def test_existing_tokens_refresh_and_revoke_with_original_client_ids(self):
        applications = self.create_duplicate_clients()
        saved_tokens = []
        for application in applications:
            status, tokens = self.exchange_code(application, self.authorize(application))
            self.assertEqual(status, 200, tokens)
            saved_tokens.append(tokens)

        call_command(Command(), stdout=StringIO())
        self.assertEqual(self.discover()['client_id'], applications[0].client_id)

        # A token must still be bound to its own client; selecting another ID must not bypass this.
        status, error = self.token_request(
            grant_type='refresh_token', client_id=applications[0].client_id,
            refresh_token=saved_tokens[1]['refresh_token'],
        )
        self.assertEqual(status, 400)
        self.assertEqual(error['error'], 'invalid_grant')

        for application, tokens in zip(applications, saved_tokens):
            with self.subTest(application=application.pk):
                self.assertTrue(OAuth2Validator().validate_bearer_token(
                    tokens['access_token'], ['read'], SimpleNamespace(),
                ))
                status, refreshed = self.token_request(
                    grant_type='refresh_token', client_id=application.client_id,
                    refresh_token=tokens['refresh_token'],
                )
                self.assertEqual(status, 200, refreshed)
                self.assertTrue(OAuth2Validator().validate_bearer_token(
                    refreshed['access_token'], ['read'], SimpleNamespace(),
                ))
                request = self.factory.post('/core/auth/oauth2-provider/revoke/', {
                    'client_id': application.client_id,
                    'token': refreshed['refresh_token'],
                    'token_type_hint': 'refresh_token',
                }, secure=True)
                self.assertEqual(RevokeTokenView.as_view()(request).status_code, 200)
                status, error = self.token_request(
                    grant_type='refresh_token', client_id=application.client_id,
                    refresh_token=refreshed['refresh_token'],
                )
                self.assertEqual(status, 400)
                self.assertEqual(error['error'], 'invalid_grant')

    def test_invalid_pkce_verifier_is_still_rejected_after_initialization(self):
        application = get_or_create_jumpserver_client_application()
        code = self.authorize(application)
        get_or_create_jumpserver_client_application()

        status, error = self.exchange_code(application, code, verifier='wrong-verifier')
        self.assertEqual(status, 400)
        self.assertEqual(error['error'], 'invalid_grant')
