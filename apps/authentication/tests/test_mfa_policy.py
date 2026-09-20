from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from authentication.const import MFAType
from authentication.mfa.policy import get_allowed_mfa_types, get_mfa_method_status


@override_settings(SECURITY_MFA_METHODS=['otp', 'face', 'sms'])
class MFAPolicyTest(SimpleTestCase):
    def test_empty_user_policy_inherits_later_system_changes(self):
        user = SimpleNamespace(allowed_mfa_types=[])
        self.assertEqual(get_allowed_mfa_types(user), {'otp', 'face', 'sms'})
        with override_settings(SECURITY_MFA_METHODS=['otp', 'passkey']):
            self.assertEqual(get_allowed_mfa_types(user), {'otp', 'passkey'})
        self.assertEqual(user.allowed_mfa_types, [])

    def test_custom_policy_cannot_expand_system_policy(self):
        user = SimpleNamespace(allowed_mfa_types=['otp', 'passkey'])
        self.assertEqual(get_allowed_mfa_types(user), {'otp'})
        self.assertEqual(user.allowed_mfa_types, ['otp', 'passkey'])

    def test_disjoint_custom_policy_does_not_fall_back_to_system(self):
        user = SimpleNamespace(allowed_mfa_types=['passkey'])
        self.assertEqual(get_allowed_mfa_types(user), set())

    @override_settings(SECURITY_MFA_METHODS=[])
    def test_empty_system_policy_preserves_legacy_fallback(self):
        self.assertEqual(get_allowed_mfa_types(), set(MFAType.values))
        user = SimpleNamespace(allowed_mfa_types=['otp'])
        self.assertEqual(get_allowed_mfa_types(user), {'otp'})

    @override_settings(MFA_BACKENDS=['otp', 'face', 'sms'], XPACK_ENABLED=True,
                       XPACK_LICENSE_IS_VALID=True)
    @patch('authentication.mfa.policy.import_string')
    def test_capabilities_follow_backends_without_mutating_policy(self, load):
        enabled = {'otp': True, 'face': False, 'sms': True}
        load.side_effect = lambda name: SimpleNamespace(
            name=name, global_enabled=lambda: enabled[name]
        )
        def status():
            return {item['value']: item for item in get_mfa_method_status()}

        self.assertFalse(status()['face']['enabled'])
        self.assertTrue(status()['face']['allowed'])
        enabled['face'] = True
        self.assertTrue(status()['face']['enabled'])
        with override_settings(XPACK_ENABLED=False):
            self.assertFalse(status()['face']['visible'])
            self.assertFalse(status()['face']['enabled'])
        with override_settings(XPACK_LICENSE_IS_VALID=False):
            self.assertFalse(status()['face']['visible'])
        self.assertFalse(status()['passkey']['enabled'])

    @override_settings(
        MFA_BACKENDS=['authentication.mfa.MFAOtp', 'authentication.mfa.MFAFace'],
        XPACK_ENABLED=True, XPACK_LICENSE_IS_VALID=True,
        FACE_RECOGNITION_ENABLED=False,
    )
    def test_user_backends_follow_feature_switch_without_rewriting_user(self):
        from users.models import User

        user = SimpleNamespace(allowed_mfa_types=[])
        def names():
            return {backend.name for backend in User.get_user_mfa_backends(user)}

        self.assertEqual(names(), {'otp'})
        with override_settings(FACE_RECOGNITION_ENABLED=True):
            self.assertEqual(names(), {'otp', 'face'})
            with override_settings(XPACK_ENABLED=False):
                self.assertEqual(names(), {'otp'})
            with override_settings(XPACK_LICENSE_IS_VALID=False):
                self.assertEqual(names(), {'otp'})
            user.allowed_mfa_types = ['otp']
            self.assertEqual(names(), {'otp'})

    def test_capability_response_keeps_boolean_status(self):
        from settings.serializers.public import PrivateSettingSerializer

        field = PrivateSettingSerializer().fields['MFA_METHODS_STATUS']
        data = field.to_representation(get_mfa_method_status())
        self.assertEqual(len(data), 7)
        for method in data:
            for key in ('visible', 'enabled', 'allowed'):
                self.assertIsInstance(method[key], bool)
