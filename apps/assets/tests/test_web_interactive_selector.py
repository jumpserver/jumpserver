from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from assets.const import Protocol
from assets.models import Web
from assets.serializers.asset.web import WebSerializer
from assets.serializers.asset.info.spec import WebSpecSerializer
from common.serializers.dynamic import create_serializer_class


class WebInteractiveSelectorTests(SimpleTestCase):
    def test_optional_field_is_exposed_in_asset_and_spec(self):
        web = Web()
        for name in ('interactive_selector', 'success_selector'):
            self.assertEqual(getattr(web, name), '')
            for serializer in (WebSerializer(), WebSpecSerializer()):
                field = serializer.fields[name]
                self.assertFalse(field.required)
                self.assertTrue(field.allow_blank)
                self.assertEqual(field.run_validation(''), '')
        self.assertEqual(WebSerializer().validate({}), {})

    def test_selectors_are_independently_optional(self):
        serializer = WebSerializer()
        for attrs in (
            {},
            {'interactive_selector': '', 'success_selector': ''},
            {'interactive_selector': 'css=#mfa-dialog'},
            {'success_selector': 'id=dashboard'},
            {'interactive_selector': 'css=#mfa-dialog', 'success_selector': 'id=dashboard'},
        ):
            with self.subTest(attrs=attrs):
                self.assertEqual(serializer.validate(attrs.copy()), attrs)

    def test_protocol_settings_allow_blank_or_omitted_selectors(self):
        settings = Protocol.cloud_protocols()[Protocol.http]['setting']
        fields = [dict(settings[name], name=name) for name in ('interactive_selector', 'success_selector')]
        serializer_class = create_serializer_class('WebSelectorSettings', fields)
        for attrs in ({}, {'interactive_selector': '', 'success_selector': ''}, {'interactive_selector': 'id=mfa'}):
            serializer = serializer_class(data=attrs)
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data['success_selector'], '')

    def test_rejects_invalid_selector_and_checks_partial_updates(self):
        web = Web(interactive_selector='id=mfa', success_selector='id=dashboard')
        serializer = WebSerializer(instance=web, partial=True)
        with self.assertRaises(ValidationError):
            serializer.validate({'interactive_selector': 'javascript=alert(1)'})
        self.assertEqual(serializer.validate({'success_selector': ''}), {'success_selector': ''})
        self.assertEqual(serializer.validate({'name': 'Renamed'}), {'name': 'Renamed'})
        self.assertEqual(serializer.validate({'interactive_selector': ''}), {'interactive_selector': ''})
