from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from pathlib import Path

import yaml

from django.test import SimpleTestCase
from ansible.parsing.splitter import parse_kv

from assets.const.database import DatabaseTypes
from assets.automations.methods import platform_automation_methods
from accounts.automations.methods import platform_automation_methods as account_methods
from ops.const import AdHocModules, JobModules
from ops.database import database_module_matches
from ops.ansible.runner import AdHocRunner
from ops.ansible.inventory import JMSInventory
from ops.models.job import JobExecution, JMSPermedInventory
from accounts.automations.gather_account.manager import GatherAccountsManager


class DatabaseAutomationIntegrationTests(SimpleTestCase):
    types = ('dameng', 'oceanbase', 'clickhouse', 'db2')

    def constraints(self):
        # Exercise EE capabilities without depending on the developer's license.
        with patch.object(DatabaseTypes, 'get_choices', return_value=DatabaseTypes.choices):
            return DatabaseTypes.get_constrains()

    def test_api_choices_and_local_execution_include_each_database(self):
        for kind in self.types:
            with self.subTest(kind=kind):
                self.assertIn(kind, JobModules.values)
                self.assertIn(kind, AdHocModules.values)
                runner = AdHocRunner('', kind, 'database_automation')
                runner.set_local_connection()
                self.assertEqual(runner.envs['ANSIBLE_SUPER_MODE'], '1')

    def test_capabilities_have_actual_builtin_methods(self):
        methods = platform_automation_methods + account_methods
        constraints = self.constraints()
        for kind in self.types:
            for action in ('ping', 'gather_facts', 'verify_account', 'gather_accounts',
                           'change_secret', 'push_account', 'remove_account'):
                enabled = constraints[kind]['automation'].get(action + '_enabled', False)
                found = [m for m in methods if m['method'] == action and kind in m['type']]
                with self.subTest(kind=kind, action=action):
                    self.assertEqual(bool(found), enabled)

    def test_existing_database_automation_is_unchanged(self):
        constraints = self.constraints()
        for kind in ('mysql', 'mariadb', 'postgresql', 'oracle', 'sqlserver', 'mongodb'):
            self.assertTrue(constraints[kind]['automation']['change_secret_enabled'])
        self.assertFalse(constraints['redis']['automation']['ansible_enabled'])
        self.assertFalse(set(self.types).intersection(DatabaseTypes.get_community_types()))

    def test_account_verification_checks_target_not_privileged_credential(self):
        from django.conf import settings
        path = Path(settings.APPS_DIR) / 'accounts/automations/verify_account/database/native/main.yml'
        task = yaml.safe_load(path.read_text())[0]['tasks'][0]['database_automation']
        self.assertEqual(task['login_user'], '{{ account.username }}')
        self.assertEqual(task['login_password'], '{{ account.secret }}')

    def test_db2_partial_directory_visibility_is_not_account_deletion(self):
        for kind in ('db2', 'dameng'):
            asset = SimpleNamespace(id='asset-id', type=kind)
            risk = MagicMock()
            context = SimpleNamespace(
                asset_usernames_mapper={'asset-id': {'visible'}},
                ori_asset_usernames={'asset-id': {'visible', 'not-visible'}},
                ori_gathered_usernames={'asset-id': {'visible', 'not-visible'}},
                summary={'new_accounts': 0, 'lost_accounts': 0}, result={'new_accounts': [], 'lost_accounts': []},
                risk_analyser=risk, get_asset_result_metadata=lambda asset: {},
            )
            with patch('accounts.automations.gather_account.manager.GatheredAccount.objects.filter'):
                GatherAccountsManager.update_gather_accounts_status(context, asset)
            with self.subTest(kind=kind):
                self.assertEqual(risk.lost_accounts.called, kind != 'db2')

    def test_oceanbase_oracle_never_uses_a_mysql_job(self):
        for module in ('mysql', 'mariadb'):
            self.assertFalse(database_module_matches(module, 'oceanbase', 'mysql', {'tenant_mode': 'oracle'}))
        self.assertTrue(database_module_matches('oceanbase', 'oceanbase', 'mysql', {'tenant_mode': 'oracle'}))
        self.assertTrue(database_module_matches('mysql', 'mariadb', 'mariadb'))
        self.assertFalse(database_module_matches('oceanbase', 'mysql', 'mysql'))

    def test_new_module_arguments_cannot_override_connection_credentials(self):
        sql = 'SELECT "x\\\" login_password=attacker login_host=evil"'
        for kind in (*self.types, 'oracle'):
            job = SimpleNamespace(type='adhoc', module=kind, chdir='')
            module, arguments = JobExecution.compile_shell(SimpleNamespace(current_job=job, rendered_args=sql))
            parsed = parse_kv(arguments)
            with self.subTest(kind=kind):
                self.assertEqual(module, 'database_automation')
                self.assertEqual(parsed['database_type'], kind)
                self.assertEqual(parsed['login_host'], '{{login_host}}')
                self.assertEqual(parsed['login_password'], '{{login_password}}')
                self.assertEqual(parsed['connection_options'], '{{login_options}}')
                self.assertEqual(parsed['query'], sql)

    def test_inventory_preserves_tenant_tls_and_original_server_identity(self):
        host = {'jms_asset': {'address': '127.0.0.1', 'origin_address': 'db.example.test',
                             'spec_info': {'use_ssl': True, 'client_key': 'key-sentinel'}}}
        protocol = SimpleNamespace(name='mysql', setting={'tenant_mode': 'oracle'})
        JMSInventory.make_protocol_setting_vars(host, [protocol])
        self.assertEqual(host['jms_asset']['database_options']['tenant_mode'], 'oracle')
        self.assertEqual(host['jms_asset']['database_options']['server_name'], 'db.example.test')
        self.assertTrue(host['jms_asset']['database_options']['use_ssl'])

    def test_inventory_authenticates_locally_without_changing_database(self):
        for kind in self.types:
            protocol = SimpleNamespace(name='mysql' if kind == 'oceanbase' else kind, port=1234)
            asset = SimpleNamespace(type=kind, address='db.example.test', spec_info={'db_name': 'APP'})
            account = SimpleNamespace(username='dbuser', secret='secret')
            host = {'jms_asset': {'database_options': {'tenant_mode': 'mysql'}}}
            result = JMSPermedInventory.make_account_vars(SimpleNamespace(module=kind), host,
                asset, account, None, protocol, None, None, '', {})
            self.assertNotIn('error', result)
            self.assertEqual(result['login_db'], 'APP')
            self.assertEqual(result['ansible_connection'], 'local')
            self.assertEqual(result['login_options'], {'tenant_mode': 'mysql'})

    def test_new_database_jobs_do_not_bypass_masking_acls(self):
        for kind in self.types:
            protocol = SimpleNamespace(name='mysql' if kind == 'oceanbase' else kind)
            asset = SimpleNamespace(name='db', address='db.example.test',
                                    protocols=SimpleNamespace(all=lambda: [protocol]))
            context = SimpleNamespace(creator=None, inventory=SimpleNamespace(assets=[asset]),
                                      current_job=SimpleNamespace(runas='user', args='SELECT secret'))
            with patch('ops.models.job.DataMaskingRule.filter_queryset', return_value=['mask-rule']):
                with self.subTest(kind=kind), self.assertRaisesRegex(Exception, 'masking'):
                    JobExecution.check_data_masking_rules_acls(context)
