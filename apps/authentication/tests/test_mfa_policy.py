from django.test import SimpleTestCase, override_settings

from authentication.const import MFAType
from authentication.mfa.policy import get_allowed_mfa_types


class DummyUser:
    def __init__(self, allowed_mfa_types=None):
        self.allowed_mfa_types = allowed_mfa_types


class MFAPolicyTest(SimpleTestCase):
    @override_settings(SECURITY_MFA_METHODS=['otp', 'sms', 'email'])
    def test_global_methods_without_user(self):
        self.assertEqual(get_allowed_mfa_types(), {'otp', 'sms', 'email'})

    @override_settings(SECURITY_MFA_METHODS=['otp', 'sms', 'email'])
    def test_empty_user_list_inherits_global(self):
        self.assertEqual(get_allowed_mfa_types(DummyUser([])), {'otp', 'sms', 'email'})
        self.assertEqual(get_allowed_mfa_types(DummyUser(None)), {'otp', 'sms', 'email'})

    @override_settings(SECURITY_MFA_METHODS=['otp', 'sms', 'email'])
    def test_user_intersects_global(self):
        user = DummyUser(['otp', 'face'])
        self.assertEqual(get_allowed_mfa_types(user), {'otp'})

    @override_settings(SECURITY_MFA_METHODS=[])
    def test_empty_global_falls_back_to_all_types(self):
        self.assertEqual(get_allowed_mfa_types(), set(MFAType.values))
