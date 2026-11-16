import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from libs.ansible.modules_utils.database import (
    DatabaseAutomationError, DatabaseClient, identifier, json_value, safe_error,
)


class NativeDatabaseClientTests(unittest.TestCase):
    def client(self, kind='dameng', **kwargs):
        return DatabaseClient(kind, 'db.example.test', 5236, 'operator', 'login-secret', **kwargs)

    def test_identifiers_are_quoted_not_executed(self):
        self.assertEqual(identifier('u"; DROP USER admin;--'), '"u""; DROP USER admin;--"')
        for name in ('', 'u\x00', 'u\n', 'a' * 129, None):
            with self.subTest(name=name), self.assertRaises(DatabaseAutomationError):
                identifier(name)

    def test_secret_errors_do_not_echo_ddl_or_passwords(self):
        for kind in ('dameng', 'oceanbase', 'clickhouse'):
            message = safe_error(RuntimeError('ALTER USER u password top-secret'), ['top-secret'], sensitive=True)
            self.assertNotIn('top-secret', message)
            self.assertNotIn('ALTER USER', message)
        self.assertNotIn('top-secret', safe_error(RuntimeError('password top-secret'), ['top-secret']))

    def test_output_conversion_is_bounded_and_keeps_decimal_precision(self):
        self.assertEqual(json_value(Decimal('12345678901234567890.1234')), '12345678901234567890.1234')
        self.assertEqual(len(json_value('x' * 100000)), 65536)
        lob = MagicMock()
        self.assertIn('omitted', json_value(lob))
        lob.read.assert_not_called()

    def test_db2_directory_mutations_are_rejected_before_connect(self):
        client = self.client('db2')
        with patch.object(client, 'connect') as connect:
            for action in ('push_account', 'change_secret', 'remove_account'):
                with self.subTest(action=action), self.assertRaisesRegex(DatabaseAutomationError, 'OS/LDAP'):
                    client.manage_account(action, 'user', 'new-secret')
            connect.assert_not_called()

    def test_db2_requires_database_and_rejects_dsn_injection(self):
        for database in ('', 'APP;UID=attacker', 'APP\x00'):
            with self.subTest(database=database), self.assertRaises(DatabaseAutomationError):
                self.client('db2', database=database).connect()

    def test_dm_driver_uses_native_connection_with_timeout(self):
        module = MagicMock()
        client = self.client()
        with patch('libs.ansible.modules_utils.database.importlib.import_module', return_value=module):
            client.connect()
            module.connect.assert_called_once_with(user='operator', password='login-secret',
                server='db.example.test', port=5236, login_timeout=15000)
            client.close()

    def test_db2_password_is_not_interpolated_into_connection_string(self):
        module = MagicMock(SQL_ATTR_LOGIN_TIMEOUT=99)
        client = self.client('db2', database='APP')
        with patch('libs.ansible.modules_utils.database.importlib.import_module', return_value=module):
            client.connect()
            args, kwargs = module.connect.call_args
            self.assertNotIn('login-secret', args[0])
            self.assertEqual(args[1:], ('operator', 'login-secret'))
            self.assertEqual(kwargs['conn_options'], {99: 15})
            client.close()

    def test_ssl_request_never_silently_falls_back_to_plaintext(self):
        for kind in ('dameng', 'oracle'):
            with self.subTest(kind=kind), self.assertRaisesRegex(DatabaseAutomationError, 'plaintext fallback'):
                self.client(kind, options={'use_ssl': True}).connect()

    def test_oceanbase_modes_keep_routing_username(self):
        module = MagicMock()
        for mode in ('mysql', 'oracle'):
            client = self.client('oceanbase', database='APP', options={'tenant_mode': mode})
            client.user = 'operator@tenant#cluster'
            with patch('libs.ansible.modules_utils.database.importlib.import_module', return_value=module):
                client.connect()
                args = module.connect.call_args.kwargs
                self.assertEqual(args['user'], 'operator@tenant#cluster')
                self.assertEqual('database' in args, mode == 'mysql')
                client.close()

    def test_oceanbase_cannot_manage_a_different_tenant(self):
        client = self.client('oceanbase')
        client.user = 'operator@tenant#cluster'
        self.assertEqual(client.account_name('app@tenant#cluster'), 'app')
        self.assertEqual(client.account_name('app'), 'app')
        with self.assertRaises(DatabaseAutomationError):
            client.account_name('app@another-tenant')

    def test_ping_is_database_authentication_not_a_tcp_probe(self):
        for kind, suffix in (('db2', 'SYSIBM.SYSDUMMY1'), ('dameng', 'DUAL'), ('clickhouse', 'alive')):
            client = self.client(kind)
            with patch.object(client, 'rows', return_value=([{'alive': 1}], False)) as rows:
                self.assertTrue(client.ping()['is_available'])
                self.assertIn(suffix, rows.call_args.args[0])

    def test_empty_ping_result_is_not_success(self):
        with patch.object(DatabaseClient, 'rows', return_value=([], False)):
            with self.assertRaises(DatabaseAutomationError):
                self.client().ping()

    def test_rotation_never_creates_a_missing_user(self):
        client = self.client()
        with patch.object(client, 'account_exists', return_value=False), patch.object(client, 'execute') as execute:
            with self.assertRaisesRegex(DatabaseAutomationError, 'never creates'):
                client.manage_account('change_secret', 'missing', 'new-secret')
            execute.assert_not_called()

    def test_push_and_rotation_are_distinct_and_parameterized(self):
        client = self.client('oceanbase')
        for exists, verb in ((True, 'ALTER USER'), (False, 'CREATE USER')):
            with patch.object(client, 'account_exists', return_value=exists), patch.object(client, 'execute') as execute:
                client.manage_account('push_account', 'app', "p'\\; DROP USER root;--")
                sql, params = execute.call_args.args
                self.assertTrue(sql.startswith(verb))
                self.assertNotIn('DROP USER root', sql)
                self.assertEqual(params, ('app', '%', "p'\\; DROP USER root;--"))

    def test_clickhouse_uses_native_bound_password(self):
        client = self.client('clickhouse')
        with patch.object(client, 'account_exists', return_value=True), patch.object(client, 'execute') as execute:
            client.manage_account('change_secret', 'app', "p'\\; DROP USER root;--")
            sql, params = execute.call_args.args
            self.assertIn('sha256_password BY %(p0)s', sql)
            self.assertEqual(params['p0'], "p'\\; DROP USER root;--")
            self.assertNotIn('DROP USER root', sql)

    def test_dm_provision_rotate_and_remove_use_distinct_statements(self):
        client = self.client()
        for action, exists, expected in (
            ('push_account', False, 'CREATE USER "app" IDENTIFIED BY "new-secret"'),
            ('change_secret', True, 'ALTER USER "app" IDENTIFIED BY "new-secret"'),
            ('remove_account', True, 'DROP USER "app"'),
        ):
            with self.subTest(action=action), patch.object(client, 'account_exists', return_value=exists), patch.object(client, 'execute') as execute:
                result = client.manage_account(action, 'app', 'new-secret')
                self.assertTrue(result['changed'])
                self.assertEqual(execute.call_args_list[0].args[0], expected)
                if action == 'push_account':
                    self.assertEqual(execute.call_args_list[1].args[0], 'GRANT CREATE SESSION TO "app"')
                else:
                    self.assertEqual(execute.call_count, 1)

    def test_clickhouse_create_and_drop_only_the_requested_sql_user(self):
        client = self.client('clickhouse')
        for action, exists, verb in (('push_account', False, 'CREATE USER'), ('remove_account', True, 'DROP USER')):
            with self.subTest(action=action), patch.object(client, 'account_exists', return_value=exists), patch.object(client, 'execute') as execute:
                self.assertTrue(client.manage_account(action, 'app', 'new-secret')['changed'])
                self.assertTrue(execute.call_args.args[0].startswith(verb + ' "app"'))

    def test_oceanbase_removal_keeps_tenant_and_host_boundaries(self):
        client = self.client('oceanbase')
        client.user = 'operator@tenant'
        with patch.object(client, 'account_exists', return_value=True), patch.object(client, 'execute') as execute:
            self.assertTrue(client.manage_account('remove_account', 'app@tenant', host='localhost')['changed'])
            self.assertEqual(execute.call_args.args, ('DROP USER %s@%s', ('app', 'localhost')))

    def test_clickhouse_xml_and_ldap_users_cannot_be_overwritten(self):
        client = self.client('clickhouse')
        for storage in ('users_xml', 'ldap', 'unknown-provider'):
            with patch.object(client, 'rows', return_value=([{'storage': storage}], False)):
                with self.subTest(storage=storage), self.assertRaisesRegex(DatabaseAutomationError, 'XML/LDAP'):
                    client.account_exists('existing')

    def test_remove_is_idempotent_and_protects_execution_account(self):
        client = self.client()
        with patch.object(client, 'account_exists', return_value=False), patch.object(client, 'execute') as execute:
            self.assertFalse(client.manage_account('remove_account', 'missing')['changed'])
            execute.assert_not_called()
        with patch.object(client, 'account_exists', return_value=True):
            for name in ('operator', 'SYSDBA', 'SYSSSO'):
                with self.subTest(name=name), self.assertRaises(DatabaseAutomationError):
                    client.manage_account('remove_account', name)

    def test_check_mode_never_mutates(self):
        client = self.client()
        with patch.object(client, 'account_exists', return_value=True), patch.object(client, 'execute') as execute:
            self.assertTrue(client.manage_account('change_secret', 'app', 'new-secret', check_mode=True)['changed'])
            execute.assert_not_called()

    def test_account_collection_preserves_tenant_and_no_password_hashes(self):
        client = self.client('oceanbase')
        client.user = 'operator@tenant'
        with patch.object(client, 'rows', return_value=([{'username': 'app', 'host': '%'}], False)) as rows:
            result = client.accounts()
            self.assertIn('app@tenant', result)
            self.assertNotIn('password', rows.call_args.args[0].lower())

    def test_db2_collects_catalog_authorization_ids_not_os_users(self):
        client = self.client('db2')
        with patch.object(client, 'rows', return_value=([], False)) as rows:
            self.assertEqual(client.accounts(), {})
            self.assertIn('SYSIBMADM.AUTHORIZATIONIDS', rows.call_args.args[0])

    def test_partial_account_collection_is_an_error_not_an_empty_snapshot(self):
        with patch.object(DatabaseClient, 'rows', return_value=([{'username': 'app'}], True)):
            with self.assertRaisesRegex(DatabaseAutomationError, 'partial snapshot'):
                self.client().accounts()

    def test_dbapi_rows_are_bounded_and_cursor_is_closed(self):
        client = self.client()
        cursor = MagicMock(description=[('AMOUNT',)])
        cursor.fetchmany.return_value = [(Decimal('1.25'),), (Decimal('2.50'),)]
        client.connection = MagicMock()
        client.connection.cursor.return_value = cursor
        result, truncated = client.rows('SELECT amount FROM example', limit=1)
        self.assertEqual(result, [{'amount': '1.25'}])
        self.assertTrue(truncated)
        cursor.fetchmany.assert_called_once_with(2)
        cursor.close.assert_called_once()

    def test_clickhouse_ddl_and_insert_results_are_not_unpacked_as_rows(self):
        client = self.client('clickhouse')
        client.connection = MagicMock()
        for response in ([], 3):
            client.connection.execute.return_value = response
            self.assertEqual(client.rows('CREATE USER example'), ([], False))

    def test_query_keeps_the_asset_schema_context(self):
        client = self.client(database='APP')
        client.connection = MagicMock()
        with patch.object(client, 'rows', return_value=([{'value': 1}], False)) as rows:
            client.query('SELECT * FROM example')
            self.assertEqual(rows.call_args_list[0].args[0], 'SET SCHEMA "APP"')
            self.assertEqual(rows.call_args_list[1].args[0], 'SELECT * FROM example')

    def test_query_statement_boundaries_keep_quoted_semicolons(self):
        client = self.client('oceanbase')
        client.connection = MagicMock()
        with patch.object(client, 'rows', return_value=([{'value': 1}], False)) as rows:
            result = client.query("SELECT 'a;b'; SELECT 2;")
            self.assertEqual(len(result['query_result']), 2)
            self.assertEqual(rows.call_args_list[0].args[0], "SELECT 'a;b';")
            client.connection.commit.assert_called_once()

    def test_oracle_family_delimiters_and_blocks_are_distinct(self):
        client = self.client()
        client.connection = MagicMock()
        with patch.object(client, 'rows', return_value=([{'value': 1}], False)) as rows:
            client.query('SELECT 1 FROM DUAL;')
            self.assertEqual(rows.call_args.args[0], 'SELECT 1 FROM DUAL')
            client.query('BEGIN NULL; NULL; END;')
            self.assertEqual(rows.call_args.args[0], 'BEGIN NULL; NULL; END;')

    def test_script_error_rolls_back_without_claiming_success(self):
        client = self.client()
        client.connection = MagicMock()
        with patch.object(client, 'rows', side_effect=[([], False), RuntimeError('query failed')]):
            with self.assertRaises(RuntimeError):
                client.query('UPDATE example SET value=1; SELECT broken FROM example;')
            client.connection.rollback.assert_called_once()
            client.connection.commit.assert_not_called()

    def test_result_files_are_removed_on_connection_close(self):
        client = self.client(options={'client_key': 'private-key-sentinel'})
        path = client.certificate_file('client_key')
        import os
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        client.close()
        self.assertFalse(os.path.exists(path))
