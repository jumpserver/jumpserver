from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from users.filters import UserFilter
from users.models import User
from users.utils import LoginBlockUtil, MFABlockUtils


class BlockedUsernameTests(SimpleTestCase):
    @patch('users.utils.cache.keys')
    def test_preserves_complete_usernames_for_login_and_mfa(self, cache_keys):
        usernames = [
            'admin', 'admin_test', '_admin', 'admin__test', 'admin_',
            '_login_block_service', '测试_用户',
        ]
        for block_util in (LoginBlockUtil, MFABlockUtils):
            with self.subTest(block_util=block_util.__name__):
                cache_keys.return_value = [
                    block_util.BLOCK_KEY_TMPL.format(username)
                    for username in usernames
                ]
                self.assertEqual(block_util.get_blocked_usernames(), usernames)

    @patch('users.utils.cache.keys', return_value=[])
    def test_returns_empty_list_when_no_users_are_blocked(self, cache_keys):
        for block_util in (LoginBlockUtil, MFABlockUtils):
            with self.subTest(block_util=block_util.__name__):
                self.assertEqual(block_util.get_blocked_usernames(), [])

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/0',
            'KEY_PREFIX': 'jumpserver',
            'VERSION': 2,
        },
    })
    def test_redis_backend_decodes_and_removes_cache_namespace(self):
        redis = Mock()
        for block_util in (LoginBlockUtil, MFABlockUtils):
            with self.subTest(block_util=block_util.__name__):
                logical_key = block_util.BLOCK_KEY_TMPL.format('admin_test')
                redis.keys.return_value = [cache.make_key(logical_key).encode()]
                with patch.object(cache.client, 'get_client', return_value=redis):
                    self.assertEqual(
                        block_util.get_blocked_usernames(), ['admin_test'],
                    )


class UserLoginBlockedFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = User.objects.bulk_create([
            User(username=username, name=username, email=f'{username}@example.com')
            for username in ('regular', 'admin_test', 'test')
        ])
        cls.user_ids = [user.id for user in users]

    def filtered_usernames(self, value):
        queryset = User.objects.filter(id__in=self.user_ids)
        filtered = UserFilter(
            data={'is_login_blocked': value}, queryset=queryset,
        )
        self.assertTrue(filtered.is_valid(), filtered.errors)
        return set(filtered.qs.values_list('username', flat=True))

    @patch('users.utils.cache.keys', return_value=['_LOGIN_BLOCK_admin_test'])
    def test_blocked_filter_matches_full_username_without_matching_suffix(self, cache_keys):
        self.assertEqual(self.filtered_usernames('true'), {'admin_test'})

    @patch('users.utils.cache.keys', return_value=['_LOGIN_BLOCK_admin_test'])
    def test_unblocked_filter_excludes_only_the_blocked_username(self, cache_keys):
        self.assertEqual(self.filtered_usernames('false'), {'regular', 'test'})

    @patch('users.utils.cache.keys', return_value=[])
    def test_filters_when_no_users_are_blocked(self, cache_keys):
        self.assertEqual(self.filtered_usernames('true'), set())
        self.assertEqual(
            self.filtered_usernames('false'), {'regular', 'admin_test', 'test'},
        )
