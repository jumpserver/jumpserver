from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from accounts.api.account.account import AccountViewSet
from accounts.exceptions import TemplateFollowingConflict
from accounts.models import Account
from accounts.tests.test_template_follow import FollowSerializer


class TemplateCredentialOverrideTests(SimpleTestCase):
    def setUp(self):
        self.account = Account(source='template', source_id='template-id', follow_template=True)
        self.account._save_with_locked_previous = Mock(wraps=self.account._save_with_locked_previous)
        self.local = Account(source='local')
        self.local._save_with_locked_previous = Mock(wraps=self.local._save_with_locked_previous)

    def clear(self, data):
        with patch.object(Account.objects, 'select_for_update') as locked, \
                patch('accounts.api.account.account.transaction.atomic', return_value=nullcontext()), \
                patch('accounts.models.account.BaseAccount.save'), \
                patch.object(Account, '_get_previous_for_update', side_effect=AssertionError('Already locked')), \
                patch.object(Account, 'get_source_template', side_effect=AssertionError('No snapshot needed')):
            locked.return_value.filter.return_value = [self.local, self.account]
            return AccountViewSet().clear_secret(SimpleNamespace(data=data))

    def test_clear_requires_confirmation_before_modifying_any_account(self):
        with self.assertRaises(TemplateFollowingConflict):
            self.clear({'account_ids': ['local', 'template']})
        self.local._save_with_locked_previous.assert_not_called()
        self.account._save_with_locked_previous.assert_not_called()
        self.assertTrue(self.account.follow_template)

    def test_confirmed_clear_detaches_and_clears_in_one_save(self):
        self.clear({'account_ids': ['local', 'template'], 'follow_template': False})
        self.assertFalse(self.account.follow_template)
        self.assertFalse(self.account.secret)
        self.assertEqual(self.account.source_id, 'template-id')
        self.account._save_with_locked_previous.assert_called_once_with(ANY, update_fields=['secret', 'follow_template'])
        self.local._save_with_locked_previous.assert_called_once_with(ANY, update_fields=['secret'])

    def test_invalid_confirmation_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.clear({'follow_template': 'invalid'})
        self.account._save_with_locked_previous.assert_not_called()

    def test_secret_type_change_requests_confirmation(self):
        with self.assertRaises(TemplateFollowingConflict):
            FollowSerializer(instance=self.account).validate({'secret_type': 'ssh_key'})

    def test_confirmed_secret_edit_is_accepted(self):
        attrs = {'secret': 'new-password', 'follow_template': False}
        self.assertEqual(FollowSerializer(instance=self.account).validate(attrs), attrs)
