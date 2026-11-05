from unittest.mock import patch

from django.test import TestCase, override_settings

from authentication.models import SSHKey
from common.utils import ssh_key_gen
from users.api.profile import UserResetPKApi
from users.models import User


@override_settings(TERMINAL_SSH_KEY_LIMIT_COUNT=3)
class UserResetSSHKeyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.public_keys = [ssh_key_gen()[1] for _ in range(3)]
        # Avoid provisioning roles and sending credential notifications for fixtures.
        cls.user, cls.other_user = User.objects.bulk_create([
            User(username='ssh-reset', name='Reset user', email='reset@example.com',
                 public_key=cls.public_keys[0]),
            User(username='ssh-other', name='Other user', email='other@example.com'),
        ])
        SSHKey.objects.bulk_create([
            SSHKey(user=cls.user, name=f'key-{i}', public_key=key, is_active=i < 2)
            for i, key in enumerate(cls.public_keys)
        ] + [SSHKey(user=cls.other_user, name='other', public_key=cls.public_keys[0])])

    def setUp(self):
        notification = patch('users.api.profile.ResetSSHKeyMsg')
        self.notification = notification.start()
        self.addCleanup(notification.stop)

    def reset_keys(self):
        view = UserResetPKApi()
        with patch.object(view, 'get_object', return_value=self.user):
            view.perform_update(None)
        self.user.refresh_from_db()

    def test_reset_disables_all_keys_without_affecting_other_users(self):
        for key in self.public_keys[:2]:
            self.assertTrue(self.user.check_public_key(key))
        records = list(self.user.ssh_keys.order_by('id').values(
            'id', 'name', 'public_key', 'date_created', 'date_last_used',
        ))

        self.reset_keys()

        self.assertIsNone(self.user.public_key)
        self.assertEqual(list(self.user.ssh_keys.order_by('id').values(
            'id', 'name', 'public_key', 'date_created', 'date_last_used',
        )), records)
        self.assertFalse(self.user.ssh_keys.filter(is_active=True).exists())
        for key in self.public_keys:
            self.assertFalse(self.user.check_public_key(key))
        self.assertEqual(self.other_user.ssh_keys.count(), 1)
        self.assertTrue(self.other_user.check_public_key(self.public_keys[0]))
        self.notification.assert_called_once_with(self.user)
        self.notification.return_value.publish_async.assert_called_once_with()

    @override_settings(TERMINAL_SSH_KEY_LIMIT_COUNT=4)
    def test_reset_allows_a_new_key_when_below_the_limit(self):
        self.reset_keys()
        self.assertTrue(self.user.can_create_ssh_key())

        public_key = ssh_key_gen()[1]
        SSHKey.objects.bulk_create([
            SSHKey(user=self.user, name='new', public_key=public_key),
        ])
        self.assertTrue(self.user.check_public_key(public_key))
        for key in self.public_keys:
            self.assertFalse(self.user.check_public_key(key))

    def test_reset_preserves_records_and_total_key_limit_when_repeated(self):
        self.assertFalse(self.user.can_create_ssh_key())
        self.reset_keys()
        self.reset_keys()

        self.assertEqual(self.user.ssh_keys.count(), 3)
        self.assertFalse(self.user.ssh_keys.filter(is_active=True).exists())
        self.assertFalse(self.user.can_create_ssh_key())

    def test_reset_with_no_keys_can_be_repeated(self):
        self.user.ssh_keys.all().delete()
        self.reset_keys()
        self.reset_keys()

        self.assertFalse(self.user.ssh_keys.exists())
        self.assertIsNone(self.user.public_key)
        self.assertEqual(self.notification.return_value.publish_async.call_count, 2)
