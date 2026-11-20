from contextlib import ExitStack
from itertools import product
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings

from authentication.backends.base import JMSModelBackend
from authentication.backends.ldap import (
    LDAPAuthorizationBackend, LDAPHAAuthorizationBackend, LDAPUser,
)
from authentication.mixins import AuthMixin, AuthPreCheckMixin, authenticate
from common.utils import text_hmac_sha256
from settings.utils.ldap import LDAPTestUtil
from users.models import User


@override_settings(
    AUTH_LDAP=True,
    AUTH_LDAP_HA=True,
    AUTH_LDAP_USER_QUERY_FIELD='username',
    AUTH_LDAP_HA_USER_QUERY_FIELD='username',
    AUTH_LDAP_USER_ATTR_MAP={'username': 'uid'},
    AUTH_LDAP_HA_USER_ATTR_MAP={'username': 'uid'},
    AUTH_LDAP_ALWAYS_UPDATE_USER=False,
    AUTH_LDAP_HA_ALWAYS_UPDATE_USER=False,
    AUTH_LDAP_USER_LOGIN_ONLY_IN_USERS=False,
    AUTH_LDAP_HA_USER_LOGIN_ONLY_IN_USERS=False,
    ONLY_ALLOW_EXIST_USER_AUTH=False,
    ONLY_ALLOW_AUTH_FROM_SOURCE=True,
)
class LDAPUsernameCaseTests(TestCase):
    def setUp(self):
        self.user = User(
            username='Alice', name='Alice', email='alice@example.com',
            email_lookup=text_hmac_sha256('alice@example.com'), source=User.Source.ldap,
        )
        User.objects.bulk_create([self.user])
        self.user_count = User.objects.count()
        self.directory_username = 'Alice'

        def bind(ldap_user, password):
            if password != 'LDAP-password':
                raise LDAPUser.AuthenticationFailed('Invalid LDAP password')
            ldap_user._user_dn = f'uid={self.directory_username},dc=example,dc=com'
            ldap_user._user_attrs = {'uid': [self.directory_username]}

        # Replace only the directory bind/search boundary, keeping user resolution real.
        self.bind_patch = patch.object(
            LDAPUser, '_authenticate_user_dn', autospec=True, side_effect=bind,
        )
        self.bind = self.bind_patch.start()
        self.addCleanup(self.bind_patch.stop)

    def use_backend(self, backend_class):
        is_ha = backend_class is LDAPHAAuthorizationBackend
        source = User.Source.ldap_ha if is_ha else User.Source.ldap
        User.objects.filter(pk=self.user.pk).update(source=source)
        backend_path = settings.AUTH_BACKEND_LDAP_HA if is_ha else settings.AUTH_BACKEND_LDAP
        return override_settings(AUTHENTICATION_BACKENDS=[backend_path])

    def login(self, username):
        view = AuthMixin()
        view.request = SimpleNamespace(session={})
        view.get_auth_data = Mock(return_value=(
            username, 'LDAP-password', None, '127.0.0.1', False,
        ))
        view.raise_credential_error = Mock(side_effect=AssertionError('Login rejected'))
        with ExitStack() as stack:
            for method in (
                '_check_is_block', '_check_login_acl', '_check_password_require_reset_or_not',
                '_check_passwd_is_too_simple', '_check_passwd_need_update',
                '_check_login_page_mfa_if_need', 'mark_password_ok',
            ):
                stack.enter_context(patch.object(view, method))
            stack.enter_context(patch.object(User, 'cache_login_password_if_need'))
            stack.enter_context(patch('authentication.mixins.LoginBlockUtil'))
            stack.enter_context(patch('authentication.mixins.LoginIpBlockUtil'))
            return view.check_user_auth()

    def test_login_uses_directory_username_with_each_existing_user_setting(self):
        for backend_class, global_only, ldap_only in product(
            (LDAPAuthorizationBackend, LDAPHAAuthorizationBackend), (False, True), (False, True),
        ):
            with self.subTest(backend=backend_class, global_only=global_only, ldap_only=ldap_only):
                with self.use_backend(backend_class), override_settings(
                    ONLY_ALLOW_EXIST_USER_AUTH=global_only,
                    AUTH_LDAP_USER_LOGIN_ONLY_IN_USERS=ldap_only,
                    AUTH_LDAP_HA_USER_LOGIN_ONLY_IN_USERS=ldap_only,
                ):
                    for username in ('Alice', 'alice', 'ALICE'):
                        user = self.login(username)
                        self.assertEqual(user.pk, self.user.pk)
                        self.assertEqual(user.username, 'Alice')
                        self.assertEqual(User.objects.count(), self.user_count)

    def test_case_collision_is_resolved_by_directory_not_input(self):
        other = User(username='alice', email='other@example.com', source=User.Source.local)
        User.objects.bulk_create([other])
        for backend_class in (LDAPAuthorizationBackend, LDAPHAAuthorizationBackend):
            with self.subTest(backend=backend_class), self.use_backend(backend_class):
                user = authenticate(username='alice', password='LDAP-password')
                self.assertEqual(user.pk, self.user.pk)
                self.assertNotEqual(user.pk, other.pk)
                self.assertEqual(User.objects.count(), self.user_count + 1)

    def test_missing_canonical_user_cannot_borrow_case_variant_when_existing_only(self):
        self.directory_username = 'ALICE'
        for backend_class, global_only, ldap_only in product(
            (LDAPAuthorizationBackend, LDAPHAAuthorizationBackend), (False, True), (False, True),
        ):
            if not (global_only or ldap_only):
                continue
            with self.subTest(backend=backend_class, global_only=global_only, ldap_only=ldap_only):
                with self.use_backend(backend_class), override_settings(
                    ONLY_ALLOW_EXIST_USER_AUTH=global_only,
                    AUTH_LDAP_USER_LOGIN_ONLY_IN_USERS=ldap_only,
                    AUTH_LDAP_HA_USER_LOGIN_ONLY_IN_USERS=ldap_only,
                ), patch('authentication.mixins.user_login_failed.send'), patch.object(User, 'save') as save:
                    self.assertIsNone(authenticate(username='Alice', password='LDAP-password'))
                    save.assert_not_called()
                    self.assertEqual(User.objects.count(), self.user_count)

    def test_unknown_directory_user_is_rejected_before_save(self):
        self.directory_username = 'NewUser'
        with self.use_backend(LDAPAuthorizationBackend), override_settings(
            ONLY_ALLOW_EXIST_USER_AUTH=True,
        ), patch.object(User, 'save') as save:
            self.assertIsNone(LDAPAuthorizationBackend().authenticate(
                username='newuser', password='LDAP-password',
            ))
            save.assert_not_called()

    def test_new_user_can_still_be_built_when_existing_only_is_disabled(self):
        backend = LDAPAuthorizationBackend()
        directory_user = SimpleNamespace(attrs={'uid': ['NewUser']})
        user, built = backend.get_or_build_user('newuser', directory_user)
        self.assertTrue(built)
        self.assertTrue(user._state.adding)
        self.assertEqual(user.username, 'NewUser')
        self.assertEqual(User.objects.count(), self.user_count)

    def test_canonical_user_source_is_checked_before_attributes_are_updated(self):
        User.objects.filter(pk=self.user.pk).update(source=User.Source.local)
        for backend_class in (LDAPAuthorizationBackend, LDAPHAAuthorizationBackend):
            with self.subTest(backend=backend_class), override_settings(
                AUTH_LDAP_ALWAYS_UPDATE_USER=True, AUTH_LDAP_HA_ALWAYS_UPDATE_USER=True,
            ), patch.object(LDAPUser, '_populate_user') as populate, patch.object(User, 'save') as save:
                self.assertIsNone(backend_class().authenticate(
                    username='alice', password='LDAP-password',
                ))
                populate.assert_not_called()
                save.assert_not_called()

    @override_settings(ONLY_ALLOW_AUTH_FROM_SOURCE=False, ONLY_ALLOW_EXIST_USER_AUTH=True)
    def test_existing_local_user_can_use_ldap_when_source_restriction_is_disabled(self):
        User.objects.filter(pk=self.user.pk).update(source=User.Source.local)
        user = LDAPAuthorizationBackend().authenticate(username='alice', password='LDAP-password')
        self.assertEqual(user.pk, self.user.pk)

    def test_password_is_passed_unchanged_and_wrong_case_is_rejected(self):
        self.assertIsNone(LDAPAuthorizationBackend().authenticate(
            username='alice', password='ldap-password',
        ))
        self.assertEqual(self.bind.call_args.args[1], 'ldap-password')
        self.assertEqual(self.bind.call_args.args[0]._username, 'alice')

    @override_settings(ONLY_ALLOW_EXIST_USER_AUTH=True, ONLY_ALLOW_AUTH_FROM_SOURCE=False)
    def test_non_ldap_backend_preserves_exact_username_and_email_lookup(self):
        backend = JMSModelBackend()
        self.assertTrue(backend.username_allow_authenticate('Alice'))
        self.assertTrue(backend.username_allow_authenticate('alice@example.com'))
        self.assertFalse(backend.username_allow_authenticate('alice'))
        self.assertFalse(backend.username_allow_authenticate('new-user'))

    @override_settings(ONLY_ALLOW_EXIST_USER_AUTH=True, ONLY_ALLOW_AUTH_FROM_SOURCE=False)
    def test_local_login_still_requires_the_exact_username_or_email(self):
        User.objects.filter(pk=self.user.pk).update(
            password=make_password('Local-password'), source=User.Source.local,
        )
        with override_settings(AUTHENTICATION_BACKENDS=[settings.AUTH_BACKEND_MODEL]), patch(
            'authentication.mixins.user_login_failed.send',
        ):
            for username in ('Alice', 'alice@example.com'):
                user = authenticate(username=username, password='Local-password')
                self.assertEqual(user.pk, self.user.pk)
            for username in ('alice', 'ALICE', 'new-user'):
                self.assertIsNone(authenticate(username=username, password='Local-password'))

    @override_settings(ONLY_ALLOW_EXIST_USER_AUTH=True)
    def test_redirect_backends_can_resolve_identity_without_a_submitted_username(self):
        self.assertTrue(JMSModelBackend().username_allow_authenticate(None))

    @override_settings(ONLY_ALLOW_EXIST_USER_AUTH=True)
    def test_sso_and_ukey_existing_user_precheck_remains_exact(self):
        view = AuthPreCheckMixin()
        view.raise_credential_error = Mock(side_effect=ValueError('Unknown user'))
        view._check_only_allow_exists_user_auth('Alice')
        with self.assertRaises(ValueError):
            view._check_only_allow_exists_user_auth('alice')

    def test_settings_login_test_uses_the_same_canonical_user_check(self):
        for backend_class in (LDAPAuthorizationBackend, LDAPHAAuthorizationBackend):
            with self.subTest(backend=backend_class), self.use_backend(backend_class), override_settings(
                AUTH_LDAP_USER_LOGIN_ONLY_IN_USERS=True,
                AUTH_LDAP_HA_USER_LOGIN_ONLY_IN_USERS=True,
            ):
                util = object.__new__(LDAPTestUtil)
                util.backend = backend_class()
                with patch('settings.utils.ldap.cache.get', return_value=True):
                    self.directory_username = 'Alice'
                    self.assertTrue(util.test_login('alice', 'LDAP-password')[0])
                    self.directory_username = 'NewUser'
                    with patch.object(User, 'save') as save:
                        self.assertFalse(util.test_login('newuser', 'LDAP-password')[0])
                        save.assert_not_called()
