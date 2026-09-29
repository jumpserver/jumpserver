from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings
from django.utils.translation import override as override_language
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory

from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.credential_client.documentation import (
    DOCUMENTATION_LANGUAGES,
    SDK_LANGUAGES,
    documentation_language,
    get_sdk_documentation,
)


class SDKDocumentationTests(SimpleTestCase):
    def request_documentation(self, language=None):
        params = {} if language is None else {'language': language}
        request = APIRequestFactory().get('/api/v1/accounts/integration-applications/sdks/', params)
        return IntegrationApplicationViewSet.as_view(
            {'get': 'get_sdks_info'}, authentication_classes=[], permission_classes=[AllowAny],
        )(request)

    def test_all_clients_have_localized_guides_and_existing_examples(self):
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
                        for tab in ('agent', 'sdk'):
                            self.assertIn(f'<!-- {tab}-doc:start -->', data['readme'])
                            self.assertIn(f'<!-- {tab}-doc:end -->', data['readme'])
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
            (client / 'demo.py').write_text('from jms_pam import Client', encoding='utf-8')
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
