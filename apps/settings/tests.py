import ssl
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from jumpserver.rewriting.smtp import EmailBackend
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
