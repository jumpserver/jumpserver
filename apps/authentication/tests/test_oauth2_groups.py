from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from authentication.backends.oauth2.backends import OAuth2Backend
from users.signal_handlers import on_oauth2_create_or_update_user, sync_oauth2_user_groups


class OAuth2GroupMappingTests(SimpleTestCase):
    def setUp(self):
        self.backend = object.__new__(OAuth2Backend)
        self.user = SimpleNamespace(id='user-1', username='alice')
        self.user_model = SimpleNamespace(objects=Mock())
        self.user_model.objects.get_or_create.return_value = (self.user, False)
        self.model_patch = patch(
            'authentication.backends.oauth2.backends.get_user_model',
            return_value=self.user_model,
        )
        self.email_patch = patch(
            'authentication.backends.oauth2.backends.construct_user_email',
            return_value='alice@example.com',
        )
        self.signal_patch = patch(
            'authentication.backends.oauth2.backends.oauth2_create_or_update_user.send'
        )
        self.model_patch.start()
        self.email_patch.start()
        self.send_signal = self.signal_patch.start()
        self.addCleanup(self.model_patch.stop)
        self.addCleanup(self.email_patch.stop)
        self.addCleanup(self.signal_patch.stop)

    def userinfo_attrs(self, mapping, userinfo):
        with override_settings(AUTH_OAUTH2_USER_ATTR_MAP=mapping):
            self.send_signal.reset_mock()
            # The transaction wrapper needs a database; the mocked user manager does not.
            OAuth2Backend.get_or_create_user_from_userinfo.__wrapped__(
                self.backend, None, userinfo
            )
        defaults = self.user_model.objects.get_or_create.call_args.kwargs['defaults']
        self.assertNotIn('groups', defaults)
        return self.send_signal.call_args.kwargs['attrs']

    def test_unconfigured_groups_are_ignored_even_when_userinfo_contains_them(self):
        attrs = self.userinfo_attrs(
            {'username': 'login'}, {'login': 'alice', 'groups': ['dev']}
        )
        self.assertNotIn('groups', attrs)

    def test_current_mapping_supplies_string_or_list(self):
        base = {'username': 'login'}
        attrs = self.userinfo_attrs(
            {**base, 'groups': 'department'},
            {'login': 'alice', 'department': 'dev', 'groups': ['old']},
        )
        self.assertEqual(attrs['groups'], 'dev')

        attrs = self.userinfo_attrs(
            {**base, 'groups': 'groups'},
            {'login': 'alice', 'groups': ['dev', 'ops']},
        )
        self.assertEqual(attrs['groups'], ['dev', 'ops'])

    def test_missing_group_field_is_distinct_from_explicit_empty_values(self):
        mapping = {'username': 'login', 'groups': 'department'}
        self.assertNotIn(
            'groups', self.userinfo_attrs(mapping, {'login': 'alice'})
        )
        self.assertEqual(
            self.userinfo_attrs(mapping, {'login': 'alice', 'department': ''})['groups'],
            '',
        )
        self.assertEqual(
            self.userinfo_attrs(mapping, {'login': 'alice', 'department': []})['groups'],
            [],
        )

    @patch('users.signal_handlers.user_authenticated_handle')
    @patch('users.signal_handlers.sync_oauth2_user_groups')
    def test_signal_syncs_only_when_mapped_field_was_returned(self, sync, handle):
        on_oauth2_create_or_update_user(None, self.user, False, {'name': 'Alice'})
        sync.assert_not_called()

        on_oauth2_create_or_update_user(
            None, self.user, False, {'name': 'Alice', 'groups': ''}
        )
        sync.assert_called_once_with(self.user, '')
        self.assertEqual(handle.call_args.args[3], {'name': 'Alice'})

        with override_settings(ONLY_ALLOW_EXIST_USER_AUTH=True):
            sync.reset_mock()
            on_oauth2_create_or_update_user(
                None, self.user, True, {'groups': ['dev']}
            )
            sync.assert_not_called()


class OAuth2GroupSyncTests(SimpleTestCase):
    @override_settings(OAUTH2_ORG_IDS=['org-1'])
    def test_sync_reconciles_only_oauth2_prefixed_memberships(self):
        user = SimpleNamespace(id='user-1', groups=Mock())
        stale = SimpleNamespace(name='OAuth2_old')
        with patch('users.signal_handlers.bind_user_to_group') as bind, patch(
            'users.signal_handlers.tmp_to_root_org', return_value=nullcontext()
        ), patch('users.signal_handlers.UserGroup.objects.filter') as groups, patch(
            'users.signal_handlers.transaction.on_commit'
        ):
            groups.return_value.exclude.return_value = [stale]
            sync_oauth2_user_groups(user, ['dev', 'ops'])

        self.assertEqual(set(bind.call_args.args[1]), {'OAuth2_dev', 'OAuth2_ops'})
        self.assertEqual(bind.call_args.kwargs, {'ignore_conflicts': True})
        self.assertEqual(groups.call_args.kwargs, {
            'org_id__in': ['org-1'],
            'name__startswith': 'OAuth2_',
            'users': user,
        })
        user.groups.remove.assert_called_once_with(stale)
        groups.return_value.delete.assert_not_called()

    @override_settings(OAUTH2_ORG_IDS=['org-1'])
    def test_explicit_empty_string_and_list_remove_old_memberships(self):
        user = SimpleNamespace(id='user-1', groups=Mock())
        stale = SimpleNamespace(name='OAuth2_old')
        with patch('users.signal_handlers.bind_user_to_group') as bind, patch(
            'users.signal_handlers.tmp_to_root_org', return_value=nullcontext()
        ), patch('users.signal_handlers.UserGroup.objects.filter') as groups, patch(
            'users.signal_handlers.transaction.on_commit'
        ):
            groups.return_value.exclude.return_value = [stale]
            for empty in ('', []):
                with self.subTest(empty=empty):
                    bind.reset_mock()
                    user.groups.remove.reset_mock()
                    sync_oauth2_user_groups(user, empty)
                    bind.assert_called_once_with(
                        ['org-1'], [], user, ignore_conflicts=True
                    )
                    user.groups.remove.assert_called_once_with(stale)

    def test_invalid_group_values_do_not_change_memberships(self):
        user = SimpleNamespace(id='user-1', groups=Mock())
        with patch('users.signal_handlers.bind_user_to_group') as bind, patch(
            'users.signal_handlers.UserGroup.objects.filter'
        ) as groups:
            for value in (None, [''], [42], ['x' * 128]):
                sync_oauth2_user_groups(user, value)
        bind.assert_not_called()
        groups.assert_not_called()
        user.groups.remove.assert_not_called()
