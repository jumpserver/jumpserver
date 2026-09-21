import json
from types import SimpleNamespace
from unittest.mock import patch

import requests
from django.test import RequestFactory, SimpleTestCase, override_settings

from authentication.backends.oidc import backends, middleware
from authentication.backends.oidc.utils import _get_jwks_keys
from jumpserver.conf import Config


TOKEN_URL = 'https://idp.example.test/token'
USERINFO_URL = 'https://idp.example.test/userinfo'
JWKS_URL = 'https://idp.example.test/jwks'


@override_settings(
    AUTH_OPENID=True,
    AUTH_OPENID_PROVIDER_TOKEN_ENDPOINT=TOKEN_URL,
    AUTH_OPENID_PROVIDER_USERINFO_ENDPOINT=USERINFO_URL,
    AUTH_OPENID_PROVIDER_JWKS_ENDPOINT=JWKS_URL,
    AUTH_OPENID_CLIENT_ID='client-id',
    AUTH_OPENID_CLIENT_SECRET='client-secret',
    AUTH_OPENID_CLIENT_AUTH_METHOD='client_secret_basic',
    AUTH_OPENID_USE_STATE=True,
    AUTH_OPENID_USE_NONCE=True,
    AUTH_OPENID_ID_TOKEN_INCLUDE_CLAIMS=False,
    AUTH_OPENID_SHARE_SESSION=True,
    BASE_SITE_URL='https://jumpserver.example.test',
)
class OIDCTLSVerificationTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(is_valid=True)
        self.claims = {'sub': 'oidc-user', 'preferred_username': 'oidc-user'}
        self.sent = {}
        self.original_merge = requests.Session.merge_environment_settings
        self.enterContext(patch.dict('os.environ', {
            'REQUESTS_CA_BUNDLE': '', 'CURL_CA_BUNDLE': '',
        }))
        self.enterContext(patch.object(
            requests.adapters.HTTPAdapter, 'send', autospec=True,
            side_effect=self.send_response,
        ))
        self.enterContext(patch.object(
            backends.UserMixin, 'get_or_create_user_from_claims',
            return_value=(self.user, False),
        ))
        for module in (backends, middleware):
            self.enterContext(patch.object(
                module, 'validate_and_return_id_token', return_value=self.claims,
            ))

    def new_request(self):
        request = RequestFactory().get('/', {'code': 'code', 'state': 'state'})
        request.session = {'oidc_auth_refresh_token': 'refresh-token'}
        return request

    def send_response(self, adapter, request, **kwargs):
        self.sent[request.url] = kwargs['verify']
        # An unrelated caller must retain its own policy while OIDC is in flight.
        self.assertIs(requests.Session.merge_environment_settings, self.original_merge)
        with requests.Session() as session:
            session.trust_env = False
            merged = session.merge_environment_settings(
                'https://unrelated.example.test/', {}, None, True, None,
            )
            self.assertIs(merged['verify'], True)

        payloads = {
            TOKEN_URL: {
                'id_token': 'id-token', 'access_token': 'access-token',
                'refresh_token': 'new-refresh-token',
            },
            USERINFO_URL: self.claims,
            JWKS_URL: {'keys': []},
        }
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(payloads[request.url]).encode()
        response.request = request
        response.url = request.url
        return response

    def assert_verification_policy(self, action, urls):
        for ignore in (False, True):
            with self.subTest(ignore=ignore), override_settings(
                AUTH_OPENID_IGNORE_SSL_VERIFICATION=ignore,
            ):
                self.sent.clear()
                action()
                self.assertEqual(self.sent, {url: not ignore for url in urls})

    def test_ignore_verification_default_is_preserved(self):
        self.assertIs(Config.defaults['AUTH_OPENID_IGNORE_SSL_VERIFICATION'], True)

    def test_authorization_code_token_and_userinfo_verification(self):
        backend = backends.OIDCAuthCodeBackend()
        self.assert_verification_policy(
            lambda: self.assertIs(
                backend.authenticate(self.new_request(), nonce='nonce'), self.user,
            ),
            (TOKEN_URL, USERINFO_URL),
        )

    def test_password_token_and_userinfo_verification(self):
        backend = backends.OIDCAuthPasswordBackend()
        self.assert_verification_policy(
            lambda: self.assertIs(
                backend.authenticate(self.new_request(), 'oidc-user', 'password'), self.user,
            ),
            (TOKEN_URL, USERINFO_URL),
        )

    def test_refresh_token_verification(self):
        refresh = middleware.OIDCRefreshIDTokenMiddleware(lambda request: None)

        def refresh_token():
            request = self.new_request()
            refresh.refresh_token(request)
            self.assertEqual(request.session['oidc_auth_refresh_token'], 'new-refresh-token')

        self.assert_verification_policy(refresh_token, (TOKEN_URL,))

    def test_jwks_verification(self):
        self.assert_verification_policy(lambda: _get_jwks_keys('client-secret'), (JWKS_URL,))
