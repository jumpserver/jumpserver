import json
import re
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, quote, urlsplit
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from jumpserver.middleware import SafeRedirectMiddleware
from jumpserver.views.other import RedirectConfirm


TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [Path(__file__).resolve().parents[2] / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': []},
}]


@override_settings(TEMPLATES=TEMPLATES, ALLOWED_HOSTS=['testserver'], USE_X_FORWARDED_HOST=False)
class RedirectConfirmTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def confirm(self, target):
        request = self.factory.get('/core/redirect/confirm/', {'next': target})
        return RedirectConfirm.as_view()(request)

    def callback_from_html(self, html):
        match = re.search(r"const targetUrl = '([^'\r\n]*)';", html)
        self.assertIsNotNone(match)
        # escapejs uses Unicode escapes, which JSON decodes the same way as JavaScript.
        return json.loads('"' + match.group(1) + '"')

    def test_confirmation_accepts_client_and_web_urls(self):
        for target in (
            'jms2://auth/callback?code=abc&state=xyz',
            'jms2://AbC+/DeF==',
            'http://127.0.0.1:14876/auth/callback?code=abc&state=xyz',
            'https://sso.example/login?next=%2Fui%2F',
        ):
            with self.subTest(target=target):
                response = self.confirm(target)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context_data['target_url'], target)

    def test_oauth_redirect_reaches_confirmation_without_changing_callback_parameters(self):
        for scheme in ('jms2',):
            with self.subTest(scheme=scheme):
                target = f'{scheme}://auth/callback?code=a%2Bb%26amp%3Bc&state=matching-state'
                request = self.factory.get('/core/auth/oauth2-provider/authorize/')
                request.resolver_match = SimpleNamespace(namespace='authentication:oauth2-provider')
                authorization = HttpResponse(status=302, headers={'Location': target})
                middleware = SafeRedirectMiddleware(lambda _: authorization)
                with patch('jumpserver.middleware.reverse', return_value='/core/redirect/confirm/'):
                    response = middleware(request)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response['Location'], f'/core/redirect/confirm/?next={quote(target)}')

                confirmation = RedirectConfirm.as_view()(self.factory.get(response['Location']))
                self.assertEqual(confirmation.status_code, 200)
                html = confirmation.render().content.decode()
                callback = self.callback_from_html(html)
                self.assertEqual(callback, target)
                self.assertEqual(parse_qs(urlsplit(callback).query), {
                    'code': ['a+b&amp;c'], 'state': ['matching-state'],
                })

    def test_encoded_client_callback_query_reaches_confirmation(self):
        request = self.factory.get(
            '/core/redirect/confirm/?next=jms2%3A//auth/callback%3Fcode%3Dtest-code%26state%3Dtest_state'
        )
        response = RedirectConfirm.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.callback_from_html(response.render().content.decode()),
            'jms2://auth/callback?code=test-code&state=test_state',
        )

    def test_javascript_url_literal_preserves_parameters_and_cannot_escape_script(self):
        target = "https://example.com/callback?code=a%2Bb&state=x'\"</script><script>alert(1)</script>"
        response = self.confirm(target)
        html = response.render().content.decode()

        self.assertEqual(self.callback_from_html(html), target)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertNotIn('const targetUrl = \'https://example.com/callback?code=a%2Bb&amp;state=', html)

    def test_invalid_schemes_and_malformed_urls_remain_rejected(self):
        for target in (
            'jms://auth/callback', 'jms://AbC+/DeF==', '', '/ui/', '//example.com/path', 'javascript://example.com/alert(1)',
            'data://text/html,test', 'file://host/path', 'ftp://example.com/file',
            'jms2:/auth/callback', 'jms2://', 'https://[invalid',
        ):
            with self.subTest(target=target):
                response = self.confirm(target)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.content, b'Invalid next url')
