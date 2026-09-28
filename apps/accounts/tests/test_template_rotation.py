from collections import defaultdict
from contextlib import ExitStack, nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from accounts.automations.change_secret.manager import ChangeSecretManager
from accounts.automations.push_account.manager import PushAccountManager
from accounts.models import Account
from assets.models import Asset


class TemplateRotationTests(SimpleTestCase):
    def make_manager(self, manager_class=ChangeSecretManager):
        account = Account(name='custom', username='user', asset=Asset(name='host'),
                          source='template', source_id='template-id', follow_template=True)
        account.save = Mock()
        record = SimpleNamespace(account=account, asset=account.asset, new_secret='rotated-secret', id='record-id')
        manager = object.__new__(manager_class)
        manager.name_record_mapper = {'host': record}
        manager.summary = defaultdict(int)
        manager.result = defaultdict(list)
        manager.save_record = Mock()
        manager.clear_account_queue_status = Mock()
        manager.print_final_host_result = Mock()
        return manager, account

    def run_result(self, manager, probe=None, failed=False):
        with ExitStack() as stack:
            stack.enter_context(patch('accounts.automations.base.manager.safe_atomic_db_connection', return_value=nullcontext()))
            stack.enter_context(patch('accounts.automations.base.manager.transaction.atomic', return_value=nullcontext()))
            stack.enter_context(patch('assets.automations.base.manager.BasePlaybookManager.on_host_success'))
            stack.enter_context(patch('assets.automations.base.manager.BasePlaybookManager.on_host_error'))
            stack.enter_context(patch.object(manager, 'get_inconclusive_probe', return_value=probe))
            if failed:
                manager.on_host_error('host', 'remote failure', {})
            else:
                manager.on_host_success('host', {})

    def test_success_detaches_and_saves_new_credentials_together(self):
        manager, account = self.make_manager()
        self.run_result(manager)
        self.assertFalse(account.follow_template)
        self.assertEqual(account.secret, 'rotated-secret')
        self.assertEqual(account.source_id, 'template-id')
        fields = account.save.call_args.kwargs['update_fields']
        self.assertIn('follow_template', fields)
        self.assertIn('secret', fields)

    def test_remote_failure_preserves_following(self):
        manager, account = self.make_manager()
        self.run_result(manager, failed=True)
        self.assertTrue(account.follow_template)
        self.assertNotIn('secret', account.save.call_args.kwargs['update_fields'])

    def test_unconfirmed_result_preserves_following(self):
        manager, account = self.make_manager()
        self.run_result(manager, probe={'reason_code': 'PROBE_ERROR'})
        self.assertTrue(account.follow_template)
        self.assertNotIn('secret', account.save.call_args.kwargs['update_fields'])

    def test_confirmed_change_with_inconclusive_login_detaches(self):
        manager, account = self.make_manager()
        self.run_result(manager, probe={'change_succeeded': True, 'sync_candidate': True})
        self.assertFalse(account.follow_template)
        self.assertEqual(account.secret, 'rotated-secret')

    def test_push_keeps_template_following(self):
        manager, account = self.make_manager(PushAccountManager)
        self.run_result(manager)
        self.assertTrue(account.follow_template)
        self.assertNotIn('secret', account.save.call_args.kwargs['update_fields'])
