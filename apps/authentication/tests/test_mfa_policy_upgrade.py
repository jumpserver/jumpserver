from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from authentication.management.commands.check_mfa_policy_upgrade import assess_user


def backend(name, active=True):
    return type('Backend', (), {
        'name': name,
        '__init__': lambda self, user: None,
        'is_active': lambda self: active,
    })


@override_settings(SECURITY_MFA_METHODS=['otp'])
class MFAPolicyUpgradeTest(SimpleTestCase):
    def user(self, methods, **kwargs):
        return SimpleNamespace(
            pk='user-id', username='test-user', allowed_mfa_types=methods,
            **{'is_active': True, 'mfa_enabled': True, **kwargs},
        )

    def test_inherited_policy_is_unaffected(self):
        self.assertIsNone(assess_user(self.user([]), [backend('otp'), backend('passkey')]))

    def test_flags_loss_of_only_bound_method_even_if_other_methods_are_available(self):
        result = assess_user(self.user(['otp', 'passkey']), [backend('otp', False), backend('passkey')])
        self.assertTrue(result['requires_attention'])
        self.assertEqual(result['remaining_methods'], ['otp'])
        self.assertEqual(result['remaining_active_methods'], [])

    def test_retained_bound_method_does_not_require_attention(self):
        result = assess_user(self.user(['otp', 'passkey']), [backend('otp'), backend('passkey')])
        self.assertFalse(result['requires_attention'])
        self.assertEqual(result['remaining_active_methods'], ['otp'])

    def test_does_not_flag_user_without_enabled_mfa_or_disabled_account(self):
        for kwargs in ({'mfa_enabled': False}, {'is_active': False}):
            result = assess_user(self.user(['passkey'], **kwargs), [backend('passkey')])
            self.assertFalse(result['requires_attention'])

    @override_settings(SECURITY_MFA_METHODS=[])
    def test_empty_system_policy_keeps_legacy_behavior(self):
        self.assertIsNone(assess_user(self.user(['passkey']), [backend('passkey')]))

    @override_settings(MFA_BACKENDS=[])
    @patch('authentication.management.commands.check_mfa_policy_upgrade.User')
    @patch('authentication.management.commands.check_mfa_policy_upgrade.assess_user')
    def test_command_reports_and_optionally_fails_without_writes(self, assess, user_model):
        queryset = MagicMock()
        user_model.objects.using.return_value.exclude.return_value = queryset
        queryset.iterator.return_value = iter([self.user(['passkey'])])
        assess.return_value = {'requires_attention': True}
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command('check_mfa_policy_upgrade', database='audit', fail_on_risk=True, stdout=output)
        user_model.objects.using.assert_called_once_with('audit')
        queryset.update.assert_not_called()
        self.assertIn('"users_requiring_attention": 1', output.getvalue())
