from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import ValidationError

from common.sdk.sms.endpoint import SMS
from common.serializers.fields import PhoneField
from common.utils.verify_code import SendAndVerifyCodeUtil
from common.validators import PhoneValidator


class PhoneFieldTests(SimpleTestCase):
    def test_phone_formats_use_the_same_international_number(self):
        field = PhoneField(validators=[PhoneValidator()], allow_blank=True, allow_null=True)
        cases = (
            ('13800138000', '+8613800138000'),
            ('+86 138 0013 8000', '+8613800138000'),
            ({'code': '+86', 'phone': '13800138000'}, '+8613800138000'),
            ('+44 7911 123456', '+447911123456'),
            ('+39 02 36618 300', '+390236618300'),
            ('', ''),
            (None, None),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(field.run_validation(value), expected)

    def test_international_number_round_trip_preserves_significant_zero(self):
        field = PhoneField(validators=[PhoneValidator()])
        number = '+390236618300'
        self.assertEqual(field.run_validation(field.to_representation(number)), number)

    def test_invalid_phone_still_fails_api_validation(self):
        with self.assertRaises(ValidationError):
            PhoneField(validators=[PhoneValidator()]).run_validation('not-a-phone')


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class SMSPhoneTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    @patch('common.utils.verify_code.send_sms_async.apply_async')
    def test_legacy_phone_can_verify_code_with_country_code(self, send):
        sender = SendAndVerifyCodeUtil('13800138000', code='123456', backend='sms')
        sender.gen_and_send()

        self.assertEqual(send.call_args.kwargs['args'], ('+8613800138000',))
        verifier = SendAndVerifyCodeUtil('+8613800138000', backend='sms')
        self.assertEqual(sender.key, verifier.key)
        self.assertTrue(verifier.verify('123456'))
        self.assertIsNone(cache.get(sender.key))

    def test_explicit_cache_key_and_non_sms_targets_are_preserved(self):
        sms = SendAndVerifyCodeUtil('13800138000', backend='sms', key='custom-key')
        self.assertEqual(sms.key, 'custom-key')
        email = SendAndVerifyCodeUtil('13800138000@example.com')
        self.assertEqual(email.target, '13800138000@example.com')
        self.assertEqual(email.key, 'auth-verify-code-13800138000@example.com')

    def test_sms_gateway_normalizes_legacy_recipients(self):
        sms = object.__new__(SMS)
        sms.client = Mock()
        numbers = ['13800138000', '+44 7911 123456']
        sms.send_sms(numbers, 'sign', 'template', {'code': '123456'})

        sms.client.send_sms.assert_called_once_with(
            phone_numbers=['+8613800138000', '+447911123456'],
            sign_name='sign', template_code='template', template_param={'code': '123456'},
        )
        self.assertEqual(numbers, ['13800138000', '+44 7911 123456'])
