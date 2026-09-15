from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from assets.serializers.asset.web import WebSerializer
from assets.serializers.platform import PlatformProtocolSerializer
from authentication.models.connection_token import ConnectionToken


@override_settings(XPACK_LICENSE_IS_VALID=False)
class WebLicenseTests(SimpleTestCase):
    advanced = (
        {'allowed_urls': ['https://sso.example.com']},
        {'autofill': 'script'},
        {'script': [{'step': 1, 'command': 'click', 'target': 'id=login'}]},
        {'success_selector': 'id=done'},
        {'interactive_selector': 'id=mfa'},
    )

    def test_asset_and_platform_reject_advanced_configuration(self):
        for config in self.advanced:
            with self.subTest(config=config):
                with self.assertRaises(ValidationError):
                    WebSerializer().validate(config.copy())
                with self.assertRaises(ValidationError):
                    PlatformProtocolSerializer().validate({'name': 'http', 'setting': config})
                with override_settings(XPACK_LICENSE_IS_VALID=True):
                    self.assertEqual(WebSerializer().validate(config.copy()), config)
        self.assertNotIn('script', WebSerializer().fields['autofill'].choices)
        self.assertEqual(WebSerializer().validate({'autofill': 'basic'}), {'autofill': 'basic'})
        self.assertEqual(WebSerializer().validate({'allowed_urls': [], 'script': []}),
                         {'allowed_urls': [], 'script': []})

    def test_existing_asset_and_platform_configuration_cannot_connect(self):
        for config in self.advanced:
            for inherited in (False, True):
                with self.subTest(config=config, inherited=inherited):
                    token = SimpleNamespace(
                        is_active=True, is_expired=False, user=SimpleNamespace(is_valid=True),
                        asset=SimpleNamespace(is_active=True, spec_info={} if inherited else config),
                        protocol='http', platform=SimpleNamespace(protocols=Mock()),
                        account='user', personal_credential_id=None, date_created=timezone.now(),
                    )
                    token.platform.protocols.filter.return_value.first.return_value = SimpleNamespace(
                        setting=config if inherited else {}
                    )
                    with self.assertRaises(PermissionDenied):
                        ConnectionToken.is_valid(token)
                    with override_settings(XPACK_LICENSE_IS_VALID=True):
                        self.assertTrue(ConnectionToken.is_valid(token))
