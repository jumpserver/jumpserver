from unittest.mock import patch

from django.db import transaction
from django.test import SimpleTestCase, TestCase, RequestFactory, override_settings
from oauth2_provider.models import get_application_model
from rest_framework.test import APIRequestFactory, force_authenticate

from authentication.backends.oauth2_provider.agent import AgentAuthorizationServerView
from authentication.backends.oauth2_provider.agent_registration import AgentClientRegistrationView, configured_resource
from settings.serializers.basic import BasicSettingSerializer
from orgs.utils import tmp_to_root_org
from rbac.models import Permission, Role
from settings.api.settings import SettingsApi
from settings.models import Setting
from settings.serializers.mcp import MCPSettingSerializer
from settings.serializers.settings import SettingsSerializer
from terminal.api.component.terminal import TerminalConfig
from terminal.models import AgentApplication, Terminal
from users.models import User


@override_settings(MCP_ENABLED=False, MCP_DCR_ENABLED=False, MCP_PUBLIC_URL='', SITE_URL='https://jumpserver.example')
class MCPSettingValidationTests(SimpleTestCase):
    def test_aggregate_settings_keeps_existing_validation(self):
        serializer = SettingsSerializer(data={'SECURITY_MFA_METHODS': []}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('SECURITY_MFA_METHODS', serializer.errors)

    def test_enabling_requires_a_valid_address_including_partial_updates(self):
        serializer = MCPSettingSerializer(data={'MCP_ENABLED': True}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('MCP_PUBLIC_URL', serializer.errors)
        with self.settings(MCP_PUBLIC_URL='http://koko:5000/koko/mcp'):
            serializer = MCPSettingSerializer(data={'MCP_ENABLED': True}, partial=True)
            self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.settings(MCP_ENABLED=True, MCP_DCR_ENABLED=True, MCP_PUBLIC_URL='https://jumpserver.example/koko/mcp'):
            serializer = MCPSettingSerializer(data={'MCP_PUBLIC_URL': ''}, partial=True)
            self.assertFalse(serializer.is_valid())
            serializer = MCPSettingSerializer(data={'MCP_ENABLED': False, 'MCP_PUBLIC_URL': ''})
            self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer = MCPSettingSerializer(data={'MCP_DCR_ENABLED': True, 'MCP_PUBLIC_URL': ''})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_enabled_service_requires_a_valid_public_site(self):
        for site in ('ftp://core.example', 'https://user@core.example', 'https://core.example?next=x',
                     'https://core.example/#fragment', 'https://core.example\\path', 'https://core.example:65536'):
            with self.subTest(site=site), self.settings(SITE_URL=site, MCP_PUBLIC_URL='http://koko:5000/koko/mcp'):
                serializer = MCPSettingSerializer(data={'MCP_ENABLED': True})
                self.assertFalse(serializer.is_valid())
                self.assertIn('MCP_ENABLED', serializer.errors)
        with self.settings(MCP_ENABLED=True):
            serializer = BasicSettingSerializer(data={'SITE_URL': 'ftp://core.example'}, partial=True)
            self.assertFalse(serializer.is_valid())
            self.assertIn('SITE_URL', serializer.errors)

    def test_settings_and_registration_share_address_validation(self):
        for address in ('http://koko:5000/koko/mcp', 'https://jumpserver.example/koko/mcp',
                        'https://host/koko/mcp%23a', 'https://host/koko/mcp%3Fa', 'https://host/koko/mcp%20a',
                        'https://host/koko/%E8%B5%84%E4%BA%A7', 'https://host/koko%2Fmcp'):
            with self.subTest(address=address), self.settings(MCP_ENABLED=True, MCP_DCR_ENABLED=True, MCP_PUBLIC_URL=address):
                serializer = MCPSettingSerializer(data={'MCP_PUBLIC_URL': address})
                self.assertTrue(serializer.is_valid(), serializer.errors)
                self.assertEqual(configured_resource(), serializer.validated_data['MCP_PUBLIC_URL'])
        for address in ('ftp://host/koko/mcp', 'https://user@host/koko/mcp', 'https://host/koko/mcp/',
                        'https://host/koko/mcp?', 'https://host/koko/mcp#', 'https://host:bad/koko/mcp',
                        'https://host/koko/mcp\n', 'https://host/koko/mcp\x7f', 'https://host/\\mcp',
                        'https://host/koko/mcp%', 'https://host/koko/mcp%2F', 'https://host/koko/mcp%00',
                        'https://host/koko/mcp%7F', 'https://host/koko/mcp%ff', 'https://host/koko/mcp%5Cpath',
                        'https://host:65536/koko/mcp'):
            with self.subTest(address=address):
                serializer = MCPSettingSerializer(data={'MCP_PUBLIC_URL': address})
                self.assertFalse(serializer.is_valid())
                self.assertIn('MCP_PUBLIC_URL', serializer.errors)
                with self.settings(MCP_PUBLIC_URL=address):
                    serializer = MCPSettingSerializer(data={'MCP_ENABLED': True}, partial=True)
                    self.assertFalse(serializer.is_valid())
                    self.assertIn('MCP_PUBLIC_URL', serializer.errors)


@override_settings(MCP_ENABLED=False, MCP_DCR_ENABLED=False, MCP_PUBLIC_URL='', SITE_URL='https://jumpserver.example')
class MCPSettingsAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create(username='mcp-settings-manager')
        cls.user = User.objects.create(username='mcp-settings-user')
        role = Role.objects.create(name='MCP settings manager', scope='system')
        role.permissions.add(Permission.objects.get(content_type__app_label='settings', codename='change_auth'))
        cls.manager.system_roles.add(role)

    def setUp(self):
        self.enterContext(tmp_to_root_org())
        self.factory = APIRequestFactory()
        self.url = '/api/v1/settings/setting/?category=mcp'

    def request(self, method, user, data=None):
        request = getattr(self.factory, method)(self.url, data=data, format='json')
        force_authenticate(request, user=user)
        with transaction.atomic():
            return SettingsApi.as_view()(request)

    @override_settings(MCP_ENABLED=True, MCP_DCR_ENABLED=True, MCP_PUBLIC_URL='https://jumpserver.example/koko/mcp')
    def test_personal_mcp_configuration_is_read_only_and_requires_login(self):
        from settings.api.public import PublicSettingApi, OpenPublicSettingApi

        request = self.factory.get('/api/v1/settings/public/')
        with transaction.atomic():
            self.assertIn(PublicSettingApi.as_view()(request).status_code, (401, 403))
        force_authenticate(request, user=self.user)
        response = PublicSettingApi.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['MCP_ENABLED'])
        self.assertTrue(response.data['MCP_DCR_ENABLED'])
        self.assertEqual(response.data['MCP_PUBLIC_URL'], 'https://jumpserver.example/koko/mcp')
        open_response = OpenPublicSettingApi.as_view()(self.factory.get('/api/v1/settings/public/open/'))
        self.assertTrue({'MCP_ENABLED', 'MCP_PUBLIC_URL', 'MCP_DCR_ENABLED'}.isdisjoint(open_response.data))
        request = self.factory.patch('/api/v1/settings/public/', {'MCP_ENABLED': False}, format='json')
        force_authenticate(request, user=self.user)
        self.assertEqual(PublicSettingApi.as_view()(request).status_code, 405)

    def test_existing_auth_configuration_permission_controls_read_write_and_metadata(self):
        for method in ('get', 'patch', 'options'):
            with self.subTest(method=method):
                response = self.request(method, self.user, {'MCP_DCR_ENABLED': False} if method == 'patch' else None)
                self.assertEqual(response.status_code, 403)
        self.assertFalse(Setting.objects.filter(name__startswith='MCP_').exists())
        response = self.request('get', self.manager)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'MCP_ENABLED': False, 'MCP_DCR_ENABLED': False, 'MCP_PUBLIC_URL': ''})
        response = self.request('options', self.manager)
        self.assertEqual(response.status_code, 200)
        self.assertIn('MCP_ENABLED', response.data['actions']['PUT'])
        self.assertIn('MCP_DCR_ENABLED', response.data['actions']['PUT'])
        self.assertIn('MCP_PUBLIC_URL', response.data['actions']['PUT'])

    def test_save_refreshes_discovery_and_disable_preserves_registered_clients(self):
        resource = 'http://jumpserver.example/koko/mcp'

        def refresh_setting(name):
            Setting.refresh_item(name)
            configured_resource()  # Every intermediate configuration must be usable.

        # Exercise the normal post-commit notification and subscriber callback
        # without depending on background thread scheduling in a test transaction.
        with patch('settings.signal_handlers.setting_pub_sub.publish', side_effect=refresh_setting), \
                self.captureOnCommitCallbacks(execute=True):
            response = self.request('patch', self.manager, {'MCP_ENABLED': True, 'MCP_DCR_ENABLED': True, 'MCP_PUBLIC_URL': resource})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Setting.objects.get(name='MCP_PUBLIC_URL').cleaned_value, resource)
        self.assertEqual(configured_resource(), resource)
        metadata_request = RequestFactory().get('/.well-known/oauth-authorization-server')
        self.assertIn('registration_endpoint', AgentAuthorizationServerView().get_metadata(metadata_request))
        app = get_application_model().objects.create(
            name='MCP settings existing client', client_type='public',
            authorization_grant_type='authorization-code', registration_source='dcr',
        )
        registration = AgentApplication.objects.create(application=app, resource=resource)
        with patch('settings.signal_handlers.setting_pub_sub.publish', side_effect=refresh_setting), \
                self.captureOnCommitCallbacks(execute=True):
            response = self.request('patch', self.manager, {'MCP_ENABLED': False, 'MCP_PUBLIC_URL': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(configured_resource(), '')
        self.assertTrue(Setting.objects.get(name='MCP_DCR_ENABLED').cleaned_value)
        self.assertNotIn('registration_endpoint', AgentAuthorizationServerView().get_metadata(metadata_request))
        response = AgentClientRegistrationView.as_view()(RequestFactory().post('/register/', {}, content_type='application/json'))
        self.assertEqual(response.status_code, 404)
        registration.refresh_from_db()
        self.assertTrue(registration.is_active)
        self.assertEqual(registration.resource, resource)
        self.assertIn('MCP_DCR_ENABLED', SettingsSerializer().fields)

    def test_invalid_update_is_rejected_without_persisting_settings(self):
        response = self.request('patch', self.manager, {'MCP_ENABLED': True, 'MCP_PUBLIC_URL': ''})
        self.assertEqual(response.status_code, 400)
        self.assertIn('MCP_PUBLIC_URL', response.data)
        self.assertFalse(Setting.objects.filter(name__startswith='MCP_').exists())

    def test_component_config_and_metadata_share_core_public_origin(self):
        role = Role.objects.create(name='MCP component config', scope='system')
        role.permissions.add(Permission.objects.get(content_type__app_label='terminal', codename='view_terminalconfig'))
        self.user.system_roles.add(role)
        terminal = Terminal.objects.create(name='mcp-settings-component', type='koko', user=self.user)

        def get_config():
            request = self.factory.get('/api/v1/terminal/terminals/config/')
            force_authenticate(request, user=self.user)
            response = TerminalConfig.as_view()(request)
            self.assertEqual(response.status_code, 200, response.data)
            return response.data

        for enabled, address in ((True, 'https://jumpserver.example/koko/mcp'),
                                 (False, 'https://jumpserver.example/koko/mcp'),
                                 (False, 'http://new.example/koko/mcp'), (False, '')):
            with self.subTest(enabled=enabled, address=address), \
                    self.settings(MCP_ENABLED=enabled, MCP_DCR_ENABLED=False, MCP_PUBLIC_URL=address,
                                  SITE_URL='https://jumpserver.example:8443/ui/'):
                config = get_config()
                self.assertEqual(config['MCP_PUBLIC_URL'], address)
                self.assertEqual(config['MCP_ENABLED'], enabled)
                origin = 'https://jumpserver.example:8443'
                self.assertEqual(config['MCP_AUTHORIZATION_SERVER'], origin if enabled else '')
                metadata = AgentAuthorizationServerView().get_metadata(
                    self.factory.get('/metadata', HTTP_HOST='internal-core:8080'),
                )
                self.assertEqual(metadata['issuer'], origin)
                self.assertTrue(metadata['authorization_endpoint'].startswith(origin + '/core/'))
        with self.settings(MCP_ENABLED=True, SITE_URL='http://127.0.0.1:8080'):
            self.assertEqual(get_config()['MCP_AUTHORIZATION_SERVER'], 'http://127.0.0.1:8080')
        with self.settings(MCP_ENABLED=False, SITE_URL=''):
            self.assertEqual(get_config()['MCP_AUTHORIZATION_SERVER'], '')
        terminal.type = 'lion'
        terminal.save(update_fields=['type'])
        with self.settings(MCP_PUBLIC_URL='https://jumpserver.example/koko/mcp'):
            self.assertTrue({'MCP_ENABLED', 'MCP_PUBLIC_URL', 'MCP_AUTHORIZATION_SERVER'}.isdisjoint(get_config()))
