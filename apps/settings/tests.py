import ssl
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

from django.conf import settings
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, override_settings
from django.urls import path
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIRequestFactory

from jumpserver.conf import Config
from jumpserver.rewriting.smtp import EmailBackend
from settings.api.ldap import LDAPUserListApi
from settings.serializers.feature import ChatAISettingSerializer
from settings.serializers.cleaning import CleaningSerializer
from settings.serializers.msg import EmailSettingSerializer
from settings.ws import LdapWebsocket
from settings.utils.ldap import LDAPServerUtil
from users.models import User


class CleaningSerializerTestCase(SimpleTestCase):
    def test_application_record_retention_defaults_and_limits(self):
        field = CleaningSerializer().fields['APPLICATION_RECORD_KEEP_DAYS']

        self.assertEqual(Config.defaults['APPLICATION_RECORD_KEEP_DAYS'], 180)
        self.assertEqual(field.min_value, settings.LOG_KEEP_MIN_DAYS)
        self.assertEqual(field.max_value, 9999)


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


@override_settings(
    DEBUG_DEV=False,
    AUTH_LDAP_SERVER_URI='ldap://primary.example.test',
    AUTH_LDAP_HA_SERVER_URI='ldap://secondary.example.test',
)
class LDAPUserListApiTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.api = LDAPUserListApi.as_view(
            authentication_classes=[], permission_classes=[], throttle_classes=[],
        )
        self.cache_get = self.enterContext(patch('settings.utils.ldap.cache.get', return_value=[]))
        self.server_search = self.enterContext(patch.object(
            LDAPServerUtil, 'search', autospec=True, return_value=[],
        ))

    def get(self, **params):
        request = self.factory.get('/api/v1/settings/ldap/users/', {'limit': 1, **params})
        response = self.api(request)
        response.render()
        self.assertEqual(response['Content-Type'], 'application/json')
        return response

    def test_default_and_explicit_categories_work_on_both_query_paths(self):
        for params, category in [({}, 'ldap'), ({'category': 'ldap'}, 'ldap'),
                                 ({'category': 'ldap_ha'}, 'ldap_ha')]:
            for cache_police in ('1', '0'):
                with self.subTest(params=params, cache_police=cache_police):
                    self.cache_get.reset_mock()
                    self.server_search.reset_mock()
                    response = self.get(cache_police=cache_police, **params)
                    self.assertEqual(response.status_code, 200)
                    if cache_police == '1':
                        self.cache_get.assert_called_once_with(f'CACHE_KEY_{category.upper()}_USERS')
                        self.server_search.assert_not_called()
                    else:
                        self.assertEqual(self.server_search.call_args.args[0].config.category, category)
                        self.server_search.assert_called_once()
                        self.cache_get.assert_not_called()

    def test_invalid_categories_are_rejected_before_querying(self):
        for category in ('', 'unknown', 'LDAP'):
            for cache_police in ('1', '0'):
                with self.subTest(category=category, cache_police=cache_police):
                    response = self.get(category=category, cache_police=cache_police)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn('category', response.data)
        self.cache_get.assert_not_called()
        self.server_search.assert_not_called()

    def test_missing_server_configuration_is_a_business_error(self):
        for category in ('ldap', 'ldap_ha'):
            for server_uri in ('', None, '  '):
                for cache_police in ('1', '0'):
                    with self.subTest(category=category, server_uri=server_uri, cache_police=cache_police), \
                            self.settings(**{f'AUTH_{category.upper()}_SERVER_URI': server_uri}):
                        response = self.get(category=category, cache_police=cache_police)
                        self.assertEqual(response.status_code, 400)
                        self.assertEqual(response.data['code'], 'ldap_not_configured')
                        self.assertEqual(set(response.data), {'detail', 'code'})
        self.cache_get.assert_not_called()
        self.server_search.assert_not_called()

    def test_unsynchronized_users_have_a_structured_error(self):
        self.cache_get.return_value = None
        response = self.get(category='ldap')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'ldap_users_not_synchronized')
        self.assertEqual(set(response.data), {'detail', 'code'})

    def test_query_failures_are_logged_without_exposing_exception_text(self):
        for cache_police, query in [('1', self.cache_get), ('0', self.server_search)]:
            with self.subTest(cache_police=cache_police), patch('settings.api.ldap.logger.exception') as log:
                query.side_effect = RuntimeError('internal traceback marker')
                response = self.get(category='ldap', cache_police=cache_police)
                query.side_effect = None
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data['code'], 'ldap_query_failed')
                self.assertNotIn(b'internal traceback marker', response.content)
                log.assert_called_once()

    def test_success_keeps_user_fields_search_and_pagination(self):
        for cache_police in ('1', '0'):
            with self.subTest(cache_police=cache_police), patch('settings.api.ldap.User.objects.all') as users:
                users.return_value.values_list.return_value = ['alice']
                entries = [{'username': 'alice', 'name': 'Alice', 'email': 'alice@example.test', 'groups': ['Ops']}]
                self.cache_get.return_value = entries
                self.server_search.return_value = entries
                response = self.get(category='ldap', cache_police=cache_police, search='alice')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['count'], 1)
                self.assertEqual(response.data['results'], [{**entries[0], 'id': 'alice', 'existing': True}])
                if cache_police == '0':
                    self.assertEqual(self.server_search.call_args.kwargs['search_value'], 'alice')

    def test_schema_documents_the_category_default_and_choices(self):
        url = 'api/v1/settings/ldap/users/'
        schema = SchemaGenerator(patterns=[path(url, LDAPUserListApi.as_view())]).get_schema(public=True)
        parameters = schema['paths'][f'/{url}']['get']['parameters']
        category = next(parameter for parameter in parameters if parameter['name'] == 'category')
        self.assertEqual(category['schema']['enum'], ['ldap', 'ldap_ha'])
        self.assertEqual(category['schema']['default'], 'ldap')
        self.assertFalse(category.get('required', False))

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
        self.enterContext(patch.object(User, 'perms', property(lambda user: user._test_perms)))

        def has_system_permissions(socket, permissions):
            user = socket.scope.get('user')
            if user is None or not getattr(user, 'is_authenticated', False):
                return False
            return set(permissions).issubset(set(getattr(user, 'perms', [])))

        self.enterContext(patch.object(
            LdapWebsocket, 'has_system_permissions', has_system_permissions
        ))

    @staticmethod
    def make_user(*perms):
        user = User(username='ldap-test-user', is_active=True)
        user._is_superuser = False
        user._test_perms = list(perms)
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
