from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, override_settings
from django.contrib.auth.models import AnonymousUser

from common.local import thread_local
from jumpserver.rewriting.storage.permissions import allow_access
from orgs.models import Organization
from orgs.utils import get_current_org, tmp_to_org
from rbac.models import RoleBinding
from terminal.models import Session
from users.models import User
from users.models.user._role import RoleManager


@override_settings(VENDOR='jumpserver', AUTHENTICATION_BACKENDS=['rbac.backends.RBACBackend'])
class ReplayMediaPermissionTests(SimpleTestCase):
    def setUp(self):
        self.current_org = Organization(id=str(uuid4()), name='Current')
        self.target_org = Organization(id=str(uuid4()), name='Recording')
        self.root_org = Organization.root()
        self.enterContext(patch.object(Organization, 'orgs_mapping', {
            str(org.id): org for org in (self.current_org, self.target_org, self.root_org)
        }))
        self.enterContext(patch.object(thread_local, 'current_org_id', self.current_org.id, create=True))
        self.session = SimpleNamespace(
            id=uuid4(), org_id=self.target_org.id, org=self.target_org,
            date_start=datetime(2026, 10, 14, tzinfo=timezone.utc),
        )
        self.user = User(username='viewer')
        self.user._is_superuser = False
        self.grants = {self.target_org.id: ['terminal.view_sessionreplay']}
        self.enterContext(patch.object(RoleManager, 'get_queryset', return_value=[]))
        self.cache = self.enterContext(patch('users.models.user._role.cache'))
        self.cache.get.return_value = None
        self.find_session = self.enterContext(patch.object(Session.objects, 'filter'))
        self.find_session.return_value.first.side_effect = self.lookup_session
        self.get_perms = self.enterContext(patch.object(
            RoleBinding, 'get_user_perms', side_effect=lambda user: self.grants.get(get_current_org().id, []),
        ))

    def lookup_session(self):
        # The real OrgManager hides this session when the current org differs.
        return self.session if get_current_org().is_root() else None

    def can_read(self, name=None):
        name = name if name is not None else f'replay/2026-10-14/{self.session.id}.replay.mp4'
        request = SimpleNamespace(user=self.user, path=f'/media/{name}')
        return allow_access(SimpleNamespace(relative_name=name, request=request))

    def test_target_org_permission_works_without_switching_current_org(self):
        for current in (self.current_org, self.target_org, self.root_org):
            with self.subTest(current=current.name), tmp_to_org(current):
                self.assertTrue(self.can_read())
                self.assertEqual(get_current_org().id, current.id)
        self.find_session.assert_called_with(id=self.session.id)
        self.get_perms.assert_called_once_with(self.user)

    def test_system_permission_covering_all_orgs_allows_target(self):
        self.get_perms.side_effect = None
        self.get_perms.return_value = ['terminal.view_sessionreplay']
        self.assertTrue(self.can_read())

    def test_current_org_cached_permission_does_not_authorize_other_orgs(self):
        self.grants = {self.current_org.id: ['terminal.view_sessionreplay']}
        for current in (self.current_org, self.root_org):
            with self.subTest(current=current.name), tmp_to_org(current):
                original_perms = self.user.perms
                self.assertFalse(self.can_read())
                self.assertIs(self.user.perms, original_perms)
                self.assertEqual(get_current_org().id, current.id)
        self.assertEqual(self.user.perms, ['terminal.view_sessionreplay'])

    def test_cached_denial_in_current_org_does_not_deny_target_org(self):
        self.assertEqual(self.user.perms, [])
        self.assertTrue(self.can_read())
        self.assertEqual(self.user.perms, [])
        self.assertEqual(self.get_perms.call_count, 2)

    def test_shared_cache_is_loaded_separately_for_each_org(self):
        self.cache.get.side_effect = lambda key: {
            'perms': ['terminal.view_sessionreplay'] if key.endswith(self.target_org.id) else [],
        }
        self.assertEqual(self.user.perms, [])
        self.assertTrue(self.can_read())
        self.assertEqual(self.user.perms, [])
        self.assertTrue(self.can_read())
        self.assertEqual(self.cache.get.call_count, 2)
        self.get_perms.assert_not_called()

    def test_anonymous_and_inactive_users_are_rejected_before_lookup(self):
        for user in (AnonymousUser(), User(is_active=False)):
            with self.subTest(user=user):
                self.user = user
                self.assertFalse(self.can_read())
        self.find_session.assert_not_called()
        self.get_perms.assert_not_called()

    def test_complete_split_and_vendor_recordings_use_the_same_permissions(self):
        base = f'replay/2026-10-14/{self.session.id}'
        for suffix in ('.replay.mp4', '.cast.gz', '/session.0.part.mp4', '/session.index.v1.json'):
            for prefix in ('', 'jumpserver/'):
                with self.subTest(suffix=suffix, prefix=prefix):
                    self.grants = {self.target_org.id: ['terminal.view_sessionreplay']}
                    self.user._role_and_perms_by_org.clear()
                    self.assertTrue(self.can_read(prefix + base + suffix))
                    self.grants = {self.current_org.id: ['terminal.view_sessionreplay']}
                    self.user._role_and_perms_by_org.clear()
                    self.assertFalse(self.can_read(prefix + base + suffix))

    def test_invalid_storage_keys_remain_rejected(self):
        sid = self.session.id
        for name in (
            '', 'replay', 'replay/2026-10-14/not-a-session.replay.mp4',
            f'replay/2026-10-13/{sid}.replay.mp4', f'replay/2026-10-14/{sid}.secret',
            f'replay/2026-10-14/{sid}/../other.mp4', f'replay/2026-10-14/{sid}/',
            f'replay/2026-10-14/{sid}/..\\other.mp4',
        ):
            with self.subTest(name=name):
                self.assertFalse(self.can_read(name))

    def test_missing_session_is_rejected(self):
        self.find_session.return_value.first.side_effect = None
        self.find_session.return_value.first.return_value = None
        self.assertFalse(self.can_read())
        self.get_perms.assert_not_called()
        self.assertEqual(get_current_org().id, self.current_org.id)

    def test_missing_session_org_is_rejected(self):
        self.session.org = None
        self.assertFalse(self.can_read())
        self.get_perms.assert_not_called()

    def test_permission_error_restores_request_org(self):
        self.get_perms.side_effect = RuntimeError('permission lookup failed')
        with self.assertRaisesRegex(RuntimeError, 'permission lookup failed'):
            self.can_read()
        self.assertEqual(get_current_org().id, self.current_org.id)

    def test_lookup_error_restores_request_org(self):
        self.find_session.return_value.first.side_effect = RuntimeError('lookup failed')
        with self.assertRaisesRegex(RuntimeError, 'lookup failed'):
            self.can_read()
        self.assertEqual(get_current_org().id, self.current_org.id)
