from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from accounts.api.account.account import AccountViewSet
from accounts.exceptions import TemplateFollowingConflict
from accounts.models import Account
from accounts.tests.test_template_follow import FollowSerializer


class TemplateCredentialOverrideTests(SimpleTestCase):
    def setUp(self):
        self.account = Account(source='template', source_id='template-id', follow_template=True)
        self.account.save = Mock()
        self.local = Account(source='local')
        self.local.save = Mock()

    def clear(self, data):
        with patch.object(Account.objects, 'select_for_update') as locked, \
                patch.object(Account.objects, 'filter') as updated, \
                patch('accounts.api.account.account.transaction.atomic', return_value=nullcontext()):
            locked.return_value.filter.return_value = [self.local, self.account]
            response = AccountViewSet().clear_secret(SimpleNamespace(data=data))
            self.updated = updated
            return response

    def test_clear_requires_confirmation_before_modifying_any_account(self):
        with self.assertRaises(TemplateFollowingConflict):
            self.clear({'account_ids': ['local', 'template']})
        self.local.save.assert_not_called()
        self.account.save.assert_not_called()
        self.assertTrue(self.account.follow_template)

    def test_confirmed_clear_detaches_and_clears_in_one_save(self):
        self.clear({'account_ids': ['local', 'template'], 'follow_template': False})
        self.updated.assert_called_once_with(id__in=[self.local.id, self.account.id])
        self.updated.return_value.update.assert_called_once_with(secret=None, follow_template=False)

    def test_invalid_confirmation_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.clear({'follow_template': 'invalid'})
        self.account.save.assert_not_called()

    def test_secret_type_change_requests_confirmation(self):
        with self.assertRaises(TemplateFollowingConflict):
            FollowSerializer(instance=self.account).validate({'secret_type': 'ssh_key'})

    def test_confirmed_secret_edit_is_accepted(self):
        attrs = {'secret': 'new-password', 'follow_template': False}
        self.assertEqual(FollowSerializer(instance=self.account).validate(attrs), attrs)
