from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from assets.validators import normalize_web_origin, validate_web_script
from assets.serializers.asset.web import WebSerializer
from assets.serializers.asset.info.spec import WebSpecSerializer


class WebLoginScriptTests(SimpleTestCase):
    def test_origins_are_exact_and_normalized(self):
        self.assertEqual(normalize_web_origin('https://SSO.example.com:443/'), 'https://sso.example.com')
        for value in ('https://*.example.com', 'https://example.com/login', 'https://user@example.com',
                      'https://example.com?x', 'https://example.com#', 'https://example.com\\@evil.test',
                      'https://example.com:99999', 'file:///tmp', 'https://example.com\n'):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                normalize_web_origin(value)

    def test_asset_script_validation_allows_sso_without_extra_fields(self):
        serializer = WebSerializer()
        script = [{'step': 1, 'command': 'type', 'target': 'id=password',
                   'value': '{SECRET}', 'origin': 'https://sso.example.com'}]
        self.assertEqual(serializer.validate_script(script), script)
        with self.assertRaises(ValidationError):
            serializer.validate_script([{'step': 1, 'command': 'javascript'}])
        for name in ('allowed_origins', 'credential_origins'):
            self.assertNotIn(name, serializer.fields)
            self.assertNotIn(name, WebSpecSerializer().fields)

    def test_script_success_must_be_last_and_steps_unique(self):
        validate_web_script([
            {'step': 1, 'command': 'interactive', 'target': 'id=mfa', 'origin': 'https://sso.example.com'},
            {'step': 2, 'command': 'success', 'target': 'id=dashboard'},
        ])
        for steps in (
            [{'step': 1, 'command': 'success'}, {'step': 2, 'command': 'click'}],
            [{'step': 1, 'command': 'check'}, {'step': 1, 'command': 'click'}],
            [{'step': 1, 'command': 'javascript'}],
            [{'step': 1, 'command': 'type', 'timeout': 0}],
        ):
            with self.assertRaises(ValidationError):
                validate_web_script(steps)
