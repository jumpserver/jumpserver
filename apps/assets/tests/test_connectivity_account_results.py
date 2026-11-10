import unittest
from assets.automations.base.account_results import account_snapshot, execution_account_results

A = 'y4__4e6751a2-2815-444e-aeac-1da210347537'
B = 'Tencent__e48a0f2d-ca4b-4e0a-80f8-da3aca2c981a'


class ConnectivityAccountResultsTests(unittest.TestCase):
    def test_snapshot_whitelists_identity_and_preserves_privilege(self):
        detail = {
            'jms_asset': {'id': 'asset', 'name': 'host', 'address': 'proxy', 'origin_address': 'original', 'secret_info': {'password': 'private'}},
            'jms_account': {'id': 'account', 'name': 'root', 'username': 'root', 'privileged': True, 'secret': 'private', 'private_key_path': 'private'},
        }
        result = account_snapshot(detail, 'ping')
        self.assertEqual(result['asset_address'], 'original')
        self.assertTrue(result['privileged'])
        self.assertEqual(result['account_id'], 'account')
        self.assertNotIn('private', str(result))
        self.assertEqual(len(result), 7)

    def test_verify_snapshots_target_not_privileged_login(self):
        detail = {'jms_asset': {'id': 'asset'}, 'jms_account': {'username': 'root', 'privileged': True},
                  'account': {'id': 'target', 'username': 'deploy', 'privileged': False}}
        result = account_snapshot(detail, 'verify_account')
        self.assertEqual(result['username'], 'deploy')
        self.assertFalse(result['privileged'])
        self.assertEqual(result['account_id'], 'target')

    def test_only_completed_targets_are_rows_and_failures_take_precedence(self):
        detail = {'username': 'root', 'privileged': True, 'secret': 'private'}
        result = execution_account_results({'account_details': {A: detail, B: detail}, 'ok_assets': [A], 'fail_assets': [[A, 'authentication failed']]}, 'ping')
        self.assertEqual(len(result['rows']), 1)
        self.assertEqual(result['rows'][0]['status'], 'failed')
        self.assertEqual(result['rows'][0]['error'], 'authentication failed')
        self.assertNotIn('private', str(result))

    def test_actual_legacy_chinese_log_resolves_two_root_accounts(self):
        lines = [
            '\x1b[33m2026-11-04 16:33:44 • y4[y4.cmdb.cc] / root：正在处理，执行账号：root（用户名：root，特权账号：是）\x1b[0m',
            '2026-11-04 16:33:44 • Tencent[192.0.2.1] / root：正在处理，执行账号：root（用户名：root，特权账号：是）',
        ]
        result = execution_account_results({'ok_assets': [A, B]}, 'ping', lines)
        self.assertEqual(result['unresolved'], 0)
        self.assertEqual([r['username'] for r in result['rows']], ['root', 'root'])
        self.assertTrue(all(r['privileged'] for r in result['rows']))
        self.assertTrue(all(r['status'] == 'success' for r in result['rows']))

    def test_legacy_english_log_preserves_nonprivileged_failure(self):
        lines = ['• y4[192.0.2.1] / deploy: processing; execution account: Deployment (username: deploy, privileged: No)']
        result = execution_account_results({'fail_assets': [[A, 'denied']]}, 'ping', lines)
        self.assertEqual(result['rows'][0]['name'], 'Deployment')
        self.assertFalse(result['rows'][0]['privileged'])
        self.assertEqual(result['rows'][0]['status'], 'failed')

    def test_missing_or_ambiguous_logs_do_not_invent_accounts(self):
        lines = ['• y4[192.0.2.1] / root: processing; execution account: root (username: root, privileged: Yes)',
                 '• y4[192.0.2.2] / root: processing; execution account: root (username: root, privileged: Yes)']
        for logs in ([], lines):
            result = execution_account_results({'ok_assets': [A]}, 'ping', logs)
            self.assertEqual(result, {'rows': [], 'unresolved': 1})

    def test_legacy_verify_keeps_target_and_unknown_privilege(self):
        lines = ['• y4[192.0.2.1] / deploy: processing; execution account: root (username: root, privileged: Yes)']
        result = execution_account_results({'ok_assets': [A + '(deploy)']}, 'verify_account', lines)
        self.assertEqual(result['rows'][0]['username'], 'deploy')
        self.assertIsNone(result['rows'][0]['privileged'])
        self.assertEqual(result['rows'][0]['name'], '')

    def test_new_snapshot_is_authoritative_even_if_log_disagrees(self):
        lines = ['• y4[192.0.2.1] / root: processing; execution account: root (username: root, privileged: Yes)']
        result = execution_account_results({'ok_assets': [A], 'account_details': {A: {'username': 'deploy', 'privileged': False}}}, 'ping', lines)
        self.assertEqual(result['rows'][0]['username'], 'deploy')
        self.assertFalse(result['rows'][0]['privileged'])

    def test_duplicate_asset_names_are_not_matched_by_name_alone(self):
        duplicate = A.replace('4e6751a2-2815-444e-aeac-1da210347537', 'e48a0f2d-ca4b-4e0a-80f8-da3aca2c981a')
        lines = ['• y4[192.0.2.1] / root: processing; execution account: root (username: root, privileged: Yes)']
        result = execution_account_results({'ok_assets': [A, duplicate]}, 'ping', lines)
        self.assertEqual(result, {'rows': [], 'unresolved': 2})

    def test_unsupported_assets_without_an_account_are_not_account_results(self):
        result = execution_account_results({'error_assets': ['host without an account']}, 'ping')
        self.assertEqual(result, {'rows': [], 'unresolved': 0})

    def test_inventory_preparation_snapshots_only_runnable_accounts(self):
        from unittest.mock import Mock, patch
        from assets.automations.base.manager import PlaybookPrepareMixin

        class Manager(PlaybookPrepareMixin):
            ansible_account_prefer = None
            ansible_account_policy = 'privileged_first'
            host_callback = None

            @classmethod
            def method_type(cls):
                return 'ping'

        manager = Manager()
        manager.result = {}
        manager.format_inventory_host_label = Mock(return_value='excluded')
        detail = {
            'jms_asset': {'id': 'asset', 'name': 'host'},
            'jms_account': {'id': 'account', 'username': 'root', 'privileged': True, 'secret': 'private'},
        }
        manager.get_inventory_hosts = Mock(return_value={A: detail})
        with patch('assets.automations.base.manager.JMSInventory') as inventory_class:
            inventory = inventory_class.return_value
            inventory.exclude_host_details = {B: detail}
            inventory.exclude_hosts = {B: 'unsupported'}
            manager.generate_inventory([], '/unused/inventory.json', 'ssh')
        self.assertEqual(list(manager.result['account_details']), [A])
        self.assertEqual(manager.result['account_details'][A]['account_id'], 'account')
        self.assertNotIn('private', str(manager.result))
        manager.get_inventory_hosts.assert_called_once()
