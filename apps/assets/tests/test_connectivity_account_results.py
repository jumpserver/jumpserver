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
        result = execution_account_results({'account_details': {A: detail, B: detail}, 'ok_assets': [A], 'fail_assets': [[A, 'authentication failed']]})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'failed')
        self.assertEqual(result[0]['error'], 'authentication failed')
        self.assertNotIn('private', str(result))

    def test_unsupported_assets_without_an_account_are_not_account_results(self):
        result = execution_account_results({'error_assets': ['host without an account']})
        self.assertEqual(result, [])

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
