from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.http import HttpResponseRedirect
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse

from authentication.backends.cas.views import CASLoginView, LoginView
from common.utils import FlashMessageUtil


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
    CAS_RETRY_LOGIN=False,
    SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies',
)
class CASLoginViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_failed_authentication_redirects_to_direct_login(self):
        request = self.factory.get(
            '/api/v1/authentication/cas/login/', {'ticket': 'invalid'}
        )
        request.user = AnonymousUser()
        request.session = SessionStore()

        with patch('django_cas_ng.views.get_cas_client'), patch(
            'django_cas_ng.views.authenticate', return_value=None
        ):
            response = CASLoginView.as_view()(request)

        location = urlsplit(response.url)
        self.assertEqual(location.path, reverse('common:flash-message'))

        message_code = parse_qs(location.query)['code'][0]
        message_data = FlashMessageUtil.get_message_by_code(message_code)
        self.assertEqual(
            message_data['redirect_url'],
            reverse('authentication:login') + '?admin=1',
        )
        self.assertEqual(str(message_data['error']), 'Login failed.')

    def test_successful_response_is_unchanged(self):
        request = self.factory.get('/api/v1/authentication/cas/login/')
        expected_response = HttpResponseRedirect('/target/')

        with patch.object(LoginView, 'get', return_value=expected_response):
            response = CASLoginView.as_view()(request)

        self.assertIs(response, expected_response)
