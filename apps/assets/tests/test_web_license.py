from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from assets.const.web import WEB_ADVANCED_FIELDS
from assets.models import Web, PlatformProtocol
from assets.serializers.asset.web import WebSerializer
from assets.serializers.platform import PlatformProtocolSerializer
from authentication.models.connection_token import ConnectionToken


@override_settings(XPACK_LICENSE_IS_VALID=False)
class WebLicenseTests(SimpleTestCase):
    advanced = {
        'allowed_urls': ['https://sso.example.com'],
        'script': [{'step': 1, 'command': 'click', 'target': 'id=login'}],
        'success_selector': 'id=done',
        'interactive_selector': 'id=mfa',
    }

    def test_asset_ignores_advanced_fields_without_license(self):
        # Even malformed hidden fields from old clients must not block editing.
        invalid = {field: {'legacy': True} for field in WEB_ADVANCED_FIELDS}
        web = Web(autofill='script', **self.advanced)
        web.interactive_selector = 'legacy selector'
        for autofill in ('no', 'basic'):
            for config in (self.advanced, invalid):
                with self.subTest(autofill=autofill, config=config):
                    serializer = WebSerializer(
                        instance=web, data={'autofill': autofill, **config}, partial=True
                    )
                    self.assertTrue(serializer.is_valid(), serializer.errors)
                    self.assertEqual(serializer.validated_data, {'autofill': autofill})
        self.assertNotIn('script', WebSerializer().fields['autofill'].choices)
        self.assertEqual(web.script, self.advanced['script'])

    def test_ignored_asset_fields_do_not_apply_defaults_on_full_update(self):
        class WebSettingsSerializer(WebSerializer):
            class Meta(WebSerializer.Meta):
                fields = ['autofill', *WEB_ADVANCED_FIELDS]

        serializer = WebSettingsSerializer(instance=Web(**self.advanced), data={'autofill': 'no'})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data, {'autofill': 'no'})

    def test_platform_ignores_advanced_fields_and_preserves_existing_values(self):
        invalid = {field: {'legacy': True} for field in WEB_ADVANCED_FIELDS}
        for protocol in ('http', 'https'):
            for existing in (None, PlatformProtocol(name=protocol, setting=self.advanced.copy())):
                for with_request in (False, True):
                    with self.subTest(protocol=protocol, existing=bool(existing), request=with_request):
                        context = {'request': SimpleNamespace(query_params={'name': protocol})} if with_request else {}
                        serializer = PlatformProtocolSerializer(
                            instance=existing,
                            data={'name': protocol, 'setting': {'autofill': 'no', **invalid}},
                            context=context, partial=True,
                        )
                        self.assertTrue(serializer.is_valid(), serializer.errors)
                        setting = serializer.validated_data['setting']
                        self.assertEqual(setting['autofill'], 'no')
                        for field in WEB_ADVANCED_FIELDS:
                            if existing:
                                self.assertEqual(setting[field], self.advanced[field])
                            else:
                                self.assertNotIn(field, setting)

    def test_script_choice_is_rejected_without_license(self):
        serializer = WebSerializer(instance=Web(), data={'autofill': 'script'}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['autofill'][0].code, 'invalid_choice')
        for protocol in ('http', 'https'):
            serializer = PlatformProtocolSerializer(
                data={'name': protocol, 'setting': {'autofill': 'script'}}, partial=True
            )
            self.assertFalse(serializer.is_valid())
            self.assertEqual(serializer.errors['setting']['autofill'][0].code, 'invalid_choice')
        serializer = PlatformProtocolSerializer(context={
            'request': SimpleNamespace(query_params={'name': 'http'})
        }).get_setting_serializer()
        with self.assertRaises(ValidationError) as exc:
            serializer.fields['autofill'].run_validation('script')
        self.assertEqual(exc.exception.detail[0].code, 'invalid_choice')

    def test_nested_platform_protocols_ignore_fields_and_reject_script_choice(self):
        serializer = PlatformProtocolSerializer(data=[{
            'name': 'http', 'setting': {'autofill': 'no', **self.advanced},
        }], many=True, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data[0]['setting'], {'autofill': 'no'})
        serializer = PlatformProtocolSerializer(data=[{
            'name': 'http', 'setting': {'autofill': 'script', **self.advanced},
        }], many=True, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors[0]['setting']['autofill'][0].code, 'invalid_choice')

    @override_settings(XPACK_LICENSE_IS_VALID=True)
    def test_licensed_asset_still_validates_and_accepts_advanced_fields(self):
        serializer = WebSerializer(instance=Web(), data={'autofill': 'script', **self.advanced}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        for field in WEB_ADVANCED_FIELDS:
            self.assertEqual(serializer.validated_data[field], self.advanced[field])
        serializer = WebSerializer(
            instance=Web(autofill='script'),
            data={'script': [{'step': 1, 'command': 'legacy-command'}]}, partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('script', serializer.errors)

    @override_settings(XPACK_LICENSE_IS_VALID=True)
    def test_inactive_script_format_is_not_validated(self):
        script = [{'step': 1, 'command': 'legacy-command'}]
        for autofill in ('no', 'basic'):
            with self.subTest(autofill=autofill):
                serializer = WebSerializer(
                    instance=Web(autofill=autofill), data={'script': script}, partial=True
                )
                self.assertTrue(serializer.is_valid(), serializer.errors)
                self.assertEqual(serializer.validated_data['script'], script)

    @patch('acls.models.ConnectMethodACL.is_method_allowed', return_value=True)
    def test_existing_asset_and_platform_configuration_can_connect(self, _allowed):
        for autofill in ('no', 'basic', 'script'):
            for inherited in (False, True):
                for protocol in ('http', 'https'):
                    with self.subTest(autofill=autofill, inherited=inherited, protocol=protocol):
                        config = {'autofill': autofill, **self.advanced}
                        token = SimpleNamespace(
                            is_active=True, is_expired=False, user=SimpleNamespace(is_valid=True),
                            asset=SimpleNamespace(is_active=True, spec_info={} if inherited else config),
                            protocol=protocol, connect_method='web', platform=SimpleNamespace(protocols=Mock()),
                            account='user', personal_credential_id=None, date_created=timezone.now(),
                        )
                        token.platform.protocols.filter.return_value.first.return_value = SimpleNamespace(
                            setting=config if inherited else {}
                        )
                        self.assertTrue(ConnectionToken.is_valid(token))
