import json
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils.translation import override

from assets.automations.base.manager import BasePlaybookManager


class AutomationErrorMessageTest(SimpleTestCase):
    def test_timeout_parameter_name_is_not_reported_as_connection_timeout(self):
        error = (
            'Push SQLServer account: Unsupported parameters for '
            '(mssql_script) module: login_timeout, query_timeout'
        )

        with override('en'):
            message = BasePlaybookManager.get_user_error_message(error)

        self.assertIn('Unsupported parameters', message)
        self.assertNotIn('Connection timed out', message)

    def test_standalone_timeout_is_reported_as_connection_timeout(self):
        with override('en'):
            message = BasePlaybookManager.get_user_error_message(
                'Connect failed: login timeout expired'
            )

        self.assertIn('Connection timed out', message)


class AutomationTargetLogTest(SimpleTestCase):
    def test_account_is_not_hidden_when_username_matches_asset_name(self):
        label = BasePlaybookManager.format_inventory_host_label(
            'sqlserver(sql)',
            {
                'jms_asset': {
                    'name': 'sqlserver',
                    'address': '172.16.200.40',
                },
                'account': {'username': 'sql'},
            },
        )

        self.assertEqual(label, 'sqlserver[172.16.200.40] / sql')

    def test_target_is_logged_before_runner_starts_with_asset_and_account(self):
        host = 'postgresql_no_ssl(jym)'
        inventory = {
            'all': {
                'hosts': {
                    host: {
                        'ansible_host': '172.16.200.30',
                        'jms_asset': {
                            'name': 'postgresql no ssl',
                            'address': '172.16.200.30',
                        },
                        'jms_account': {'username': 'postgres'},
                        'account': {'username': 'jym'},
                    },
                    'localhost': {
                        'ansible_host': '127.0.0.1',
                        'ansible_connection': 'local',
                    },
                },
            },
        }
        manager = object.__new__(BasePlaybookManager)
        manager._runner_host_labels = {}
        runner = SimpleNamespace(
            id='runner-1',
            cb=SimpleNamespace(announced_hosts=set()),
        )

        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json') as f:
            json.dump(inventory, f)
            f.flush()
            with patch.object(manager, 'print_log') as print_log:
                manager.announce_runner_targets(runner, f.name)

        message, level = print_log.call_args.args
        self.assertEqual(level, 'progress')
        self.assertIn('postgresql no ssl', message)
        self.assertIn('172.16.200.30', message)
        self.assertIn('jym', message)
        self.assertNotIn(' / postgres', message)
        self.assertEqual(print_log.call_count, 1)
        self.assertEqual(runner.cb.announced_hosts, {host, 'localhost'})
        self.assertEqual(
            manager._runner_host_labels['runner-1'][host],
            'postgresql no ssl[172.16.200.30] / jym',
        )
