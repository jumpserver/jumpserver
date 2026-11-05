from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from accounts.api.account.application import IntegrationApplicationViewSet, PAMClientSourceDownloadAPI
from accounts.credential_client.access import materials
from accounts.credential_client.documentation import (
    DOCUMENTATION_LANGUAGES,
    SDK_INSTALL_COMMANDS,
    SDK_LANGUAGES,
    documentation_language,
    get_sdk_documentation,
)
from django.test import SimpleTestCase, override_settings
from django.utils.translation import override as override_language
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory


class SDKDocumentationTests(SimpleTestCase):
    def test_wizard_installs_the_same_source_revision_as_managed_examples(self):
        for command in SDK_INSTALL_COMMANDS.values():
            self.assertIn('/api/v1/accounts/client-source/', command)
            self.assertNotIn('/releases/download/v1.0.2/', command)
        application = SimpleNamespace(id='application', secret='secret', org_id='org')
        result = materials(application, {
            'type': 'agent', 'app_user': 'orders', 'install_path': '/opt/jumpserver-pam',
            'delivery_mode': 'json', 'systemd_unit': '', 'systemd_action': '',
            'store_scope': 'all', 'store_format': 'json',
        }, 'https://example.com')
        self.assertIn('https://example.com/api/v1/accounts/client-source/agent/', result['install_command'])
        self.assertIn('go -C ', result['install_command'])
        self.assertIn('&&\ntar -xzf ', result['install_command'])

    def test_source_bundles_include_installable_packages_and_agent_sdk_dependency(self):
        from io import BytesIO
        import tarfile
        expected = {
            'python': ('python/setup.py', 'python/jms_pam/client.py'),
            'go': ('go/go.mod', 'go/client.go'),
            'java': ('java/pom.xml', 'java/src/main/java/org/jumpserver/pam/Client.java'),
            'node': ('node/package.json', 'node/index.js', 'node/event-names.js'),
            'agent': ('agent/go.mod', 'agent/cmd/pam-agent/main.go', 'go/go.mod', 'go/client.go'),
            'socket': ('socket/python_example.py', 'socket/README.en.md', 'socket/README.zh-hans.md'),
        }
        for language, paths in expected.items():
            request = APIRequestFactory().get(f'/api/v1/accounts/client-source/{language}/')
            response = PAMClientSourceDownloadAPI.as_view()(request, language=language)
            self.assertEqual(response.status_code, 200)
            with tarfile.open(fileobj=BytesIO(response.content)) as archive:
                names = archive.getnames()
                for path in paths:
                    self.assertIn(f'jms-pam-clients/{path}', names)
                self.assertFalse(any('/.git' in name or '/node_modules/' in name or name.endswith('_test.go') for name in names))

    def test_source_bundle_excludes_local_identity_files_and_symlinks(self):
        from io import BytesIO
        import tarfile
        from accounts.credential_client.source import source_archive
        with TemporaryDirectory() as directory:
            python = Path(directory) / 'accounts' / 'clients' / 'python'
            (python / 'jms_pam').mkdir(parents=True)
            (python / 'jms_pam' / '__init__.py').write_text('# SDK')
            secret = python / 'jms_pam_config.py'
            secret.write_text('app_secret = "private"')
            (python / 'jms_pam' / 'linked.py').symlink_to(secret)
            with override_settings(APPS_DIR=directory):
                with tarfile.open(fileobj=BytesIO(source_archive('python'))) as archive:
                    self.assertEqual(archive.getnames(), ['jms-pam-clients/python/jms_pam/__init__.py'])

    def test_unknown_source_language_is_not_a_filesystem_path(self):
        request = APIRequestFactory().get('/api/v1/accounts/client-source/ruby/')
        for language in ('ruby', '..', '../python', 'python/setup.py'):
            response = PAMClientSourceDownloadAPI.as_view()(request, language=language)
            self.assertEqual(response.status_code, 404)

    def test_python_wizard_and_guides_share_the_event_example(self):
        application = SimpleNamespace(id='application', secret='secret', org_id='org')
        result = materials(application, {'type': 'sdk', 'sdk_language': 'python'}, 'https://example.com')
        for locale in DOCUMENTATION_LANGUAGES:
            with self.subTest(locale=locale):
                data = get_sdk_documentation('python', locale)
                self.assertEqual(result['code'], data['code'])
                self.assertIn(result['code'].rstrip(), data['readme'])

    def test_agent_materials_install_go_binary_with_fixed_service(self):
        application = SimpleNamespace(id='application', secret='secret', org_id='org')
        scope = SimpleNamespace(id='scope', app_user='orders', install_path='/opt/jumpserver-pam')
        params = {
            'type': 'agent', 'app_user': 'orders', 'install_path': scope.install_path,
            'delivery_mode': 'json', 'systemd_unit': '', 'systemd_action': '',
            'store_scope': 'all', 'store_format': 'json',
        }
        result = materials(application, params, 'https://example.com')
        import json
        config = json.loads(result['config'])
        self.assertEqual(config['socket']['owner'], 'orders')
        self.assertNotIn('instance_id', config)
        self.assertNotIn('--instance-id', result['install_command'])
        self.assertNotIn('state_file', config)
        self.assertNotIn('event_file', config)
        self.assertNotIn('path', config['socket'])
        self.assertEqual(config['store']['accounts'], ['all'])
        self.assertEqual(config['version'], 1)
        self.assertNotIn('delivery', config)
        self.assertEqual(result['service_name'], 'pam-agent')
        self.assertEqual(result['agent_language'], 'go')
        self.assertIn('/usr/local/bin/pam-agent install', result['registration_command'])
        self.assertNotIn('python', result['install_command'])
        self.assertNotIn('venv', result['install_command'])
        self.assertNotIn('pam-agent-scope', result['install_command'])

    def request_documentation(self, language=None):
        params = {} if language is None else {'language': language}
        request = APIRequestFactory().get('/api/v1/accounts/integration-applications/sdks/', params)
        return IntegrationApplicationViewSet.as_view(
            {'get': 'get_sdks_info'}, authentication_classes=[], permission_classes=[AllowAny],
        )(request)

    def test_all_clients_have_localized_guides_and_existing_examples(self):
        self.assertEqual(set(SDK_INSTALL_COMMANDS), set(SDK_LANGUAGES) - {'curl'})
        for language in SDK_LANGUAGES:
            for locale in DOCUMENTATION_LANGUAGES:
                with self.subTest(language=language, locale=locale), override_language(locale):
                    response = self.request_documentation(language)
                    self.assertEqual(response.status_code, 200)
                    data = response.data
                    self.assertEqual(data['language'], language)
                    self.assertEqual(data['documentation_language'], locale)
                    self.assertEqual(data['credential_policies'], language != 'curl')
                    self.assertTrue(data['readme'].startswith('# '))
                    self.assertTrue(data['code'])
                    self.assertEqual({item['value'] for item in data['languages']}, set(SDK_LANGUAGES) - {'curl'})
                    if language == 'python':
                        for tab in ('agent', 'sdk', 'socket'):
                            self.assertIn(f'<!-- {tab}-doc:start -->', data['readme'])
                            self.assertIn(f'<!-- {tab}-doc:end -->', data['readme'])
                        self.assertIn('from jms_pam_config import client_options, instance_id', data['readme'])
                        self.assertIn('with Client(instance_id=instance_id', data['readme'])
                    elif language == 'curl':
                        self.assertIn('/integration-applications/account-secret/', data['readme'])
                    else:
                        self.assertNotIn('/integration-applications/account-secret/', data['readme'])

    def test_language_aliases_and_unknown_language_fallback(self):
        aliases = {
            'zh': 'zh-hans', 'zh_CN': 'zh-hans', 'zh_TW': 'zh-hant',
            'zh-Hant-TW': 'zh-hant', 'pt': 'pt-br', 'pt_BR': 'pt-br',
            'en_US': 'en', 'fr-FR': 'fr', 'ja-JP': 'ja', 'de': 'en', None: 'en',
        }
        for language, expected in aliases.items():
            with self.subTest(language=language):
                self.assertEqual(documentation_language(language), expected)

    def test_missing_translation_returns_english_and_actual_locale(self):
        with TemporaryDirectory() as directory:
            client = Path(directory) / 'accounts' / 'clients' / 'python'
            client.mkdir(parents=True)
            (client / 'README.en.md').write_text('# English', encoding='utf-8')
            (client / 'subclass_demo.py').write_text('from jms_pam import Client', encoding='utf-8')
            with override_settings(APPS_DIR=directory):
                data = get_sdk_documentation('python', 'fr')
            self.assertEqual(data['documentation_language'], 'en')
            self.assertEqual(data['readme'], '# English')

    def test_unknown_sdk_or_path_is_rejected(self):
        for language in ('ruby', '../python', 'python/README.en.md', '', 'Python'):
            with self.subTest(language=language):
                response = self.request_documentation(language)
                self.assertEqual(response.status_code, 400)
                self.assertIn('language', response.data)

    def test_default_client_remains_python(self):
        with override_language('fr'):
            response = self.request_documentation()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['language'], 'python')
        self.assertEqual(response.data['documentation_language'], 'fr')
