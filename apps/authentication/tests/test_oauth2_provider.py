from datetime import timedelta
from fnmatch import fnmatchcase
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.utils import OperationalError, ProgrammingError
from django.test import TestCase, override_settings
from django.utils import timezone
from oauth2_provider.models import (
    get_access_token_model, get_application_model, get_refresh_token_model,
)

from authentication.backends.oauth2_provider.utils import get_or_create_jumpserver_client_application
from authentication.backends.oauth2_provider.signal_handlers import on_django_ready_refresh_oauth2_provider_client
from authentication.management.commands.init_oauth2_provider import Command


LEGACY_CALLBACK = 'jms://auth/callback'
CLIENT_CALLBACK = 'jms2://auth/callback'
DEV_CALLBACK = 'http://127.0.0.1:14876/auth/callback'


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
