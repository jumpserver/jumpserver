import ssl
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from jumpserver.rewriting.smtp import EmailBackend
from settings.serializers.feature import ChatAISettingSerializer
from settings.serializers.msg import EmailSettingSerializer


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
