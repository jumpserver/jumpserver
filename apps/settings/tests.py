import ssl
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, override_settings

from jumpserver.rewriting.smtp import EmailBackend
from settings.api.ldap import LDAPUserListApi
from settings.serializers.feature import ChatAISettingSerializer
from settings.serializers.msg import EmailSettingSerializer
from settings.ws import LdapWebsocket
from users.models import User


class SMTPEmailBackendTestCase(SimpleTestCase):
    @patch('django.core.mail.backends.smtp.ssl.create_default_context')
    @override_settings(
        EMAIL_CERT_VERIFY_MODE='custom_ca',
        EMAIL_CACERT_CONTENT='custom ca'
    )
    def test_custom_ca_is_added_to_default_context(self, create_context):
        context = create_context.return_value

        self.assertIs(EmailBackend().ssl_context, context)
        context.load_verify_locations.assert_called_once_with(cadata='custom ca')

    @patch('django.core.mail.backends.smtp.ssl.create_default_context')
    @override_settings(EMAIL_CERT_VERIFY_MODE='none')
    def test_certificate_verification_can_be_disabled(self, create_context):
        context = create_context.return_value

        self.assertIs(EmailBackend().ssl_context, context)
        self.assertFalse(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_NONE)


@override_settings(EMAIL_CERT_VERIFY_MODE='system', EMAIL_CACERT_CONTENT='')
class EmailSettingSerializerTestCase(SimpleTestCase):
    def get_serializer(self, **data):
        return EmailSettingSerializer(data={
            'EMAIL_HOST': 'smtp.example.test',
            'EMAIL_PORT': '587',
            **data,
        })

    def test_custom_ca_mode_requires_certificate(self):
        serializer = self.get_serializer(
            EMAIL_CERT_VERIFY_MODE='custom_ca', EMAIL_USE_TLS=True
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('EMAIL_CACERT_CONTENT', serializer.errors)

    def test_custom_ca_is_not_required_without_tls(self):
        serializer = self.get_serializer(
            EMAIL_CERT_VERIFY_MODE='custom_ca',
            EMAIL_USE_SSL=False,
            EMAIL_USE_TLS=False,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_private_key_is_rejected(self):
        serializer = self.get_serializer(
            EMAIL_CACERT_CONTENT='-----BEGIN PRIVATE KEY-----\nsecret'
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('EMAIL_CACERT_CONTENT', serializer.errors)

    def test_invalid_ca_certificate_is_rejected(self):
        serializer = self.get_serializer(EMAIL_CACERT_CONTENT='not a certificate')

        self.assertFalse(serializer.is_valid())
        self.assertIn('EMAIL_CACERT_CONTENT', serializer.errors)


@override_settings(
    CHAT_AI_ENABLED=False,
    CHAT_AI_METHOD='api',
    CHAT_AI_EMBED_URL='',
    CHAT_AI_BASE_URL='',
)
class ChatAISettingSerializerTestCase(SimpleTestCase):
    def test_enabled_api_requires_base_url(self):
        serializer = ChatAISettingSerializer(data={
            'CHAT_AI_ENABLED': True,
            'CHAT_AI_METHOD': 'api',
            'CHAT_AI_BASE_URL': '',
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('CHAT_AI_BASE_URL', serializer.errors)

    def test_enabled_api_accepts_http_url_without_embed_url(self):
        serializer = ChatAISettingSerializer(data={
            'CHAT_AI_ENABLED': True,
            'CHAT_AI_METHOD': 'api',
            'CHAT_AI_BASE_URL': 'http://models.example.test/v1',
            'CHAT_AI_EMBED_URL': '',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_enabled_iframe_requires_embed_url(self):
        serializer = ChatAISettingSerializer(data={
            'CHAT_AI_ENABLED': True,
            'CHAT_AI_METHOD': 'iframe',
            'CHAT_AI_EMBED_URL': '',
            'CHAT_AI_BASE_URL': '',
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('CHAT_AI_EMBED_URL', serializer.errors)

    def test_enabled_iframe_accepts_https_url_without_base_url(self):
        serializer = ChatAISettingSerializer(data={
            'CHAT_AI_ENABLED': True,
            'CHAT_AI_METHOD': 'iframe',
            'CHAT_AI_EMBED_URL': 'https://assistant.example.test/chat',
            'CHAT_AI_BASE_URL': '',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_iframe_rejects_non_http_urls(self):
        for embed_url in (
            'ftp://assistant.example.test/chat',
            'javascript:alert(1)',
        ):
            with self.subTest(embed_url=embed_url):
                serializer = ChatAISettingSerializer(data={
                    'CHAT_AI_ENABLED': True,
                    'CHAT_AI_METHOD': 'iframe',
                    'CHAT_AI_EMBED_URL': embed_url,
                })

                self.assertFalse(serializer.is_valid())
                self.assertIn('CHAT_AI_EMBED_URL', serializer.errors)

    @override_settings(
        CHAT_AI_ENABLED=True,
        CHAT_AI_METHOD='iframe',
        CHAT_AI_EMBED_URL='',
    )
    def test_partial_update_validates_configured_iframe_method(self):
        serializer = ChatAISettingSerializer(data={}, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn('CHAT_AI_EMBED_URL', serializer.errors)


class LDAPUserListApiTest(SimpleTestCase):
    def test_sort_ignores_missing_field(self):
        view = LDAPUserListApi()
        view.request = SimpleNamespace(query_params={'order': 'date_updated'})
        users = [{'existing': False}, {'existing': True}]

        self.assertEqual(view.sort_queryset(users), users)


@override_settings(
    AUTHENTICATION_BACKENDS=['rbac.backends.RBACBackend'],
    CHANNEL_LAYERS={},
)
class LDAPWebsocketPermissionTest(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(patch.object(User, 'lang', new_callable=PropertyMock, return_value='en'))

    @staticmethod
    def make_user(*perms):
        user = User(username='ldap-test-user', is_active=True)
        user._is_superuser = False
        user.perms = list(perms)
        return user

    @staticmethod
    def make_socket(user, category):
        socket = WebsocketCommunicator(
            LdapWebsocket.as_asgi(), f'/ws/ldap/?category={category}'
        )
        socket.scope['user'] = user
        return socket

    async def test_view_only_users_cannot_connect(self):
        for category in ('ldap', 'ldap_ha'):
            with self.subTest(category=category):
                socket = self.make_socket(
                    self.make_user('settings.view_setting'), category
                )
                try:
                    connected, _ = await socket.connect()
                    self.assertFalse(connected)
                finally:
                    await socket.disconnect()

    async def test_users_without_auth_permission_cannot_connect(self):
        for user in (
            AnonymousUser(), self.make_user(),
            self.make_user('settings.change_basic'),
        ):
            with self.subTest(user=user):
                socket = self.make_socket(user, 'ldap')
                try:
                    connected, _ = await socket.connect()
                    self.assertFalse(connected)
                finally:
                    await socket.disconnect()

    async def test_auth_settings_editors_can_test_ldap(self):
        for category in ('ldap', 'ldap_ha'):
            with self.subTest(category=category):
                socket = self.make_socket(
                    self.make_user('settings.change_auth'), category
                )
                prefix = f'AUTH_{category.upper()}'
                with patch('settings.ws.LDAPTestUtil') as test_util:
                    test_util.return_value.test_config.return_value = (False, 'Test result')
                    try:
                        connected, _ = await socket.connect()
                        self.assertTrue(connected)
                        await socket.send_json_to({
                            'msg_type': 'testing_config',
                            f'{prefix}_SERVER_URI': 'ldap://directory.example.test:389',
                            f'{prefix}_SEARCH_OU': 'dc=example,dc=test',
                            f'{prefix}_SEARCH_FILTER': '(uid=%(user)s)',
                            f'{prefix}_USER_ATTR_MAP': {
                                'username': 'uid', 'name': 'cn', 'email': 'mail',
                            },
                        })
                        response = await socket.receive_json_from()
                        self.assertEqual(response, {'ok': False, 'msg': 'Test result'})
                        test_util.return_value.test_config.assert_called_once_with()
                        self.assertEqual(test_util.call_args.kwargs['category'], category)
                    finally:
                        await socket.disconnect()
