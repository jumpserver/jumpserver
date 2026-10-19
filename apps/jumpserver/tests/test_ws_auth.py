from types import SimpleNamespace
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.test import SimpleTestCase

from jumpserver.routing import get_signature_user


class WebSocketAuthenticationTests(SimpleTestCase):
    def make_scope(self, authorization=None):
        headers = [(b'host', b'testserver')]
        if authorization:
            headers.append((b'authorization', authorization))
        return {
            'type': 'websocket',
            'path': '/ws/facelive/capture/',
            'query_string': b'',
            'headers': headers,
            'server': ('testserver', 80),
            'scheme': 'http',
        }

    def test_oauth_bearer_authenticates_face_websocket(self):
        user = SimpleNamespace(id='face-user')
        with patch('jumpserver.routing.SignatureAuthentication.authenticate', return_value=None), \
             patch('jumpserver.routing.AccessTokenAuthentication.authenticate', return_value=None), \
             patch('jumpserver.routing.OAuth2Authentication.authenticate', return_value=(user, object())) as oauth:
            result = async_to_sync(get_signature_user)(self.make_scope(b'Bearer test-token'))

        self.assertIs(result, user)
        oauth.assert_called_once()
        self.assertEqual(oauth.call_args.args[0].META['HTTP_AUTHORIZATION'], 'Bearer test-token')

    def test_missing_authorization_does_not_try_oauth(self):
        with patch('jumpserver.routing.OAuth2Authentication.authenticate') as oauth:
            result = async_to_sync(get_signature_user)(self.make_scope())

        self.assertIsNone(result)
        oauth.assert_not_called()

    def test_invalid_bearer_does_not_authenticate(self):
        with patch('jumpserver.routing.SignatureAuthentication.authenticate', return_value=None), \
             patch('jumpserver.routing.AccessTokenAuthentication.authenticate', return_value=None), \
             patch('jumpserver.routing.OAuth2Authentication.authenticate', return_value=None):
            result = async_to_sync(get_signature_user)(self.make_scope(b'Bearer invalid'))

        self.assertIsNone(result)
