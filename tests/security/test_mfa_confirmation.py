import abc
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import sys

from django.db.models import TextChoices
from source_boundary import RedisFixture, load
from test_failed_counters import ns as counters

types = load('apps/authentication/const.py', ['ConfirmType'], {'TextChoices': TextChoices, '_': lambda s: s})['ConfirmType']
base = load('apps/authentication/confirm/base.py', ['BaseConfirm'], {'abc': abc})['BaseConfirm']
ConfirmMFA = load('apps/authentication/confirm/mfa.py', ['ConfirmMFA'], {
    'BaseConfirm': base, 'ConfirmType': types, 'MFABlockUtils': counters['MFABlockUtils'],
    'get_request_ip': lambda request: '127.0.0.1', '_': lambda s: s,
    'block_mfa_msg': 'blocked for {} minutes',
})['ConfirmMFA']


class MFAConfirmation(RedisFixture, unittest.TestCase):
    def user(self, backend):
        return SimpleNamespace(username='test-user', mfa_enabled=True, active_mfa_backends=[backend],
                               get_active_mfa_backend_by_type=lambda name: backend if name == 'otp' else None)

    def test_failed_limit_and_success(self):
        backend = Mock()
        backend.check_code.return_value = False, 'invalid'
        request = SimpleNamespace(session={})
        confirm = ConfirmMFA(self.user(backend), request)
        for _ in range(7):
            self.assertFalse(confirm.authenticate('bad', 'otp')[0])
        backend.check_code.return_value = True, ''
        self.assertFalse(confirm.authenticate('correct', 'otp')[0])
        self.assertEqual(backend.check_code.call_count, 7)
        counters['MFABlockUtils']('test-user', '').clean_failed_count()
        self.assertEqual(confirm.authenticate('correct', 'otp'), (True, ''))
        self.assertEqual(request.session, {})  # No primary-login state is granted.

    def test_inactive_or_unknown_backend_and_retry_reset(self):
        backend = Mock()
        backend.check_code.return_value = True, ''
        confirm = ConfirmMFA(self.user(backend), SimpleNamespace(session={}))
        self.assertFalse(confirm.authenticate('anything', 'disabled')[0])
        backend.check_code.assert_not_called()
        self.assertEqual(counters['MFABlockUtils']('test-user', '').get_failed_count(), 1)
        confirm.authenticate('correct', 'otp')
        self.assertEqual(counters['MFABlockUtils']('test-user', '').get_failed_count(), 0)

    def test_real_confirmation_hierarchy_uses_same_boundary(self):
        module = SimpleNamespace(CONFIRM_BACKEND_MAP={'mfa': ConfirmMFA})
        with patch.dict(sys.modules, {'authentication.confirm': module}):
            for value in types.values:
                self.assertEqual(types.get_prop_backends(value), [ConfirmMFA])

    def test_successful_first_factor_does_not_clear_mfa_lock(self):
        namespace = {'User': object, 'LoginBlockUtil': counters['LoginBlockUtil'],
                     'LoginIpBlockUtil': counters['LoginIpBlockUtil'],
                     'MFABlockUtils': counters['MFABlockUtils']}
        for name in ['CommonMixin', 'AuthPreCheckMixin', 'AuthACLMixin', 'AuthFaceMixin', 'MFAMixin', 'AuthPostCheckMixin']:
            namespace[name] = type(name, (), {})
        Auth = load('apps/authentication/mixins.py', ['AuthMixin'], namespace,
                    members=['check_oauth2_auth'])['AuthMixin']
        util = counters['MFABlockUtils']('test-user', '')
        for _ in range(7):
            util.incr_failed_count()
        auth = Auth()
        auth.request = SimpleNamespace(session={})
        auth.get_request_ip = lambda: '127.0.0.1'
        for name in ['_set_partial_credential_error', '_check_is_block', '_check_login_acl', 'mark_password_ok']:
            setattr(auth, name, Mock())
        user = SimpleNamespace(username='test-user', is_expired=False, is_active=True)
        self.assertIs(auth.check_oauth2_auth(user, 'fixture-oauth'), user)
        self.assertTrue(util.is_block())
        self.assertEqual(util.get_failed_count(), 7)


if __name__ == '__main__':
    unittest.main()
