import ssl
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase
from ldap3.core.results import (
    RESULT_INSUFFICIENT_ACCESS_RIGHTS,
    RESULT_INVALID_CREDENTIALS,
    RESULT_SIZE_LIMIT_EXCEEDED,
    RESULT_SUCCESS,
    RESULT_UNAVAILABLE_CRITICAL_EXTENSION,
)

from accounts.automations.change_secret.manager import ChangeSecretManager
from assets.const import Protocol
from assets.const.ds import DirectoryTypes
from libs.ansible.modules import ad_ldap_user
from libs.ansible.modules_utils import ad_ldap
from ops.ansible.inventory import JMSInventory


class ADLdapHelperTests(SimpleTestCase):
    def test_domain_to_base_dn(self):
        self.assertEqual(ad_ldap.domain_to_base_dn('example.com'), 'DC=example,DC=com')
        self.assertEqual(ad_ldap.domain_to_base_dn(' corp.example.com. '),
                         'DC=corp,DC=example,DC=com')
        self.assertEqual(ad_ldap.domain_to_base_dn(''), '')
        with self.assertRaises(ad_ldap.ADLdapError):
            ad_ldap.domain_to_base_dn('evil,OU=x')

    def test_user_filter_accepts_ad_name_forms_and_escapes(self):
        self.assertIn('(sAMAccountName=alice)', ad_ldap.build_user_filter('alice'))
        self.assertIn('(sAMAccountName=alice)', ad_ldap.build_user_filter('CORP\\alice'))
        upn = ad_ldap.build_user_filter('alice@corp.example.com')
        self.assertIn('(userPrincipalName=alice@corp.example.com)', upn)
        self.assertIn('(sAMAccountName=alice)', upn)
        escaped = ad_ldap.build_user_filter('a*)(cn=*')
        self.assertIn('a\\2a\\29\\28cn=\\2a', escaped)
        self.assertNotIn('(cn=*', escaped)

    def test_bind_subcodes(self):
        error = ad_ldap.classify_bind_result({
            'result': RESULT_INVALID_CREDENTIALS,
            'message': '80090308: LdapErr: DSID-0C09044E, comment: '
                       'AcceptSecurityContext error, data 52e, v4563',
        })
        self.assertEqual((error.auth_status, error.reason_code),
                         ('rejected', 'AUTHENTICATION_FAILED'))
        locked = ad_ldap.classify_bind_result({
            'result': RESULT_INVALID_CREDENTIALS,
            'message': 'AcceptSecurityContext error, data 775, v4563',
        })
        self.assertEqual((locked.auth_status, locked.reason_code),
                         ('unknown', 'ACCOUNT_LOCKED'))
        must_change = ad_ldap.classify_bind_result({
            'result': RESULT_INVALID_CREDENTIALS,
            'message': 'AcceptSecurityContext error, data 773, v4563',
        })
        self.assertEqual(must_change.reason_code, 'PASSWORD_MUST_CHANGE')

    def test_modify_errors(self):
        policy = ad_ldap.classify_modify_result({
            'result': 19,
            'message': '0000052D: Constraint violation - check_password_restrictions',
        })
        self.assertEqual(policy.reason_code, 'PASSWORD_POLICY_VIOLATION')
        self.assertEqual(policy.win32_code, ad_ldap.ERROR_PASSWORD_RESTRICTION)
        access = ad_ldap.classify_modify_result({
            'result': RESULT_INSUFFICIENT_ACCESS_RIGHTS,
            'message': '00000005: SecErr: DSID-031A11E5, problem 4003',
        })
        self.assertEqual(access.reason_code, 'INSUFFICIENT_ACCESS_RIGHTS')
        hints = ad_ldap.classify_modify_result({
            'result': RESULT_UNAVAILABLE_CRITICAL_EXTENSION, 'message': '',
        })
        self.assertEqual(hints.reason_code, 'POLICY_HINTS_UNSUPPORTED')

    def test_tls_validates_by_default(self):
        tls = ad_ldap.StrictTls('dc01.corp.example.com')
        context = tls.create_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        insecure = ad_ldap.StrictTls('10.0.0.1', allow_invalid_cert=True).create_context()
        self.assertFalse(insecure.check_hostname)
        self.assertEqual(insecure.verify_mode, ssl.CERT_NONE)

    def test_tls_server_name_defaults_to_host(self):
        client = ad_ldap.ADLdapClient('10.0.0.1', 636)
        self.assertEqual(client.tls.server_name, '10.0.0.1')
        client = ad_ldap.ADLdapClient('127.0.0.1', 50000, tls_server_name='dc01.corp')
        self.assertEqual(client.tls.server_name, 'dc01.corp')
        with self.assertRaises(ad_ldap.ADLdapError):
            ad_ldap.ADLdapClient('dc01', 389, security='plain')


class FakeConnection:
    def __init__(self, response=None, result=None, modify_results=None):
        self.response = response or []
        self.result = result or {'result': RESULT_SUCCESS}
        self.modify_results = list(modify_results or [])
        self.modify_calls = []
        self.unlocked = []
        self.extend = SimpleNamespace(microsoft=SimpleNamespace(
            modify_password=self.modify_password,
            unlock_account=self.unlock_account,
        ))

    def search(self, *args, **kwargs):
        self.search_args = (args, kwargs)

    def modify_password(self, user_dn, new_password, old_password=None, controls=None):
        self.modify_calls.append((user_dn, new_password, old_password, controls))
        result = self.modify_results.pop(0) if self.modify_results else {'result': RESULT_SUCCESS}
        self.result = result
        return result['result'] == RESULT_SUCCESS

    def unlock_account(self, user_dn):
        self.unlocked.append(user_dn)
        return True


class ADLdapClientTests(SimpleTestCase):
    def setUp(self):
        self.client = ad_ldap.ADLdapClient('dc01', 636)

    def entry(self, dn):
        return {'type': 'searchResEntry', 'dn': dn}

    def test_find_user_uses_domain_base_and_requires_one_match(self):
        conn = FakeConnection(response=[self.entry('CN=Alice,OU=Staff,DC=corp,DC=test')])
        dn = self.client.find_user(conn, 'alice', domain_name='corp.test')
        self.assertEqual(dn, 'CN=Alice,OU=Staff,DC=corp,DC=test')
        self.assertEqual(conn.search_args[0][0], 'DC=corp,DC=test')

        conn = FakeConnection(response=[self.entry('CN=A'), self.entry('CN=B')])
        with self.assertRaises(ad_ldap.ADLdapError) as ctx:
            self.client.find_user(conn, 'alice', domain_name='corp.test')
        self.assertEqual(ctx.exception.reason_code, 'USER_AMBIGUOUS')

        conn = FakeConnection(result={'result': RESULT_SIZE_LIMIT_EXCEEDED},
                              response=[self.entry('CN=A')])
        with self.assertRaises(ad_ldap.ADLdapError):
            self.client.find_user(conn, 'alice', domain_name='corp.test')

        with self.assertRaises(ad_ldap.ADLdapError) as ctx:
            self.client.find_user(FakeConnection(), 'alice', domain_name='corp.test')
        self.assertEqual(ctx.exception.reason_code, 'USER_NOT_FOUND')

        with self.assertRaises(ad_ldap.ADLdapError) as ctx:
            self.client.find_user(FakeConnection(), 'alice')
        self.assertEqual(ctx.exception.reason_code, 'SEARCH_BASE_REQUIRED')

    def test_set_password_controls(self):
        conn = FakeConnection()
        self.client.set_password(conn, 'CN=A', 'new')
        self.assertEqual(conn.modify_calls[-1], ('CN=A', 'new', None, None))

        self.client.set_password(conn, 'CN=A', 'new', enforce_history=True)
        controls = conn.modify_calls[-1][3]
        self.assertEqual(controls, [(ad_ldap.POLICY_HINTS_OID, True, ad_ldap.POLICY_HINTS_VALUE)])

        # The user change operation enforces history by itself.
        self.client.set_password(conn, 'CN=A', 'new', old_password='old', enforce_history=True)
        self.assertEqual(conn.modify_calls[-1], ('CN=A', 'new', 'old', None))

        conn = FakeConnection(modify_results=[{
            'result': 19, 'message': '0000052D: Constraint violation',
        }])
        with self.assertRaises(ad_ldap.ADLdapError) as ctx:
            self.client.set_password(conn, 'CN=A', 'new')
        self.assertEqual(ctx.exception.reason_code, 'PASSWORD_POLICY_VIOLATION')


class ADLdapUserModuleTests(SimpleTestCase):
    def make_module(self, **params):
        defaults = {
            'login_user': 'pam@corp.test', 'login_password': 'pam-secret',
            'name': 'alice', 'password': 'New-Secret-1', 'old_password': '',
            'mode': 'reset', 'enforce_password_history': False, 'unlock': False,
            'domain_name': 'corp.test', 'search_base': '', 'change_started_at': 1_800_000_000,
        }
        defaults.update(params)
        return SimpleNamespace(params=defaults, check_mode=False)

    def setUp(self):
        # JumpServer's clock; the DC clock defaults to the same time.
        patcher = mock.patch.object(ad_ldap_user.time, 'time', return_value=1_800_000_200)
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_client(self, conn, check_status='accepted', pwd_last_set=1_800_000_100,
                    server_time=1_800_000_200):
        client = ad_ldap.ADLdapClient('dc01', 636)
        client.bind = mock.Mock(return_value=conn)
        client.unbind = mock.Mock()
        client.check_password = mock.Mock(return_value=(check_status, 'X', ''))
        client.get_pwd_last_set = mock.Mock(return_value=pwd_last_set)
        client.get_server_time = mock.Mock(return_value=server_time)
        return client

    def test_reset_changes_password_and_unlocks(self):
        conn = FakeConnection(response=[{'type': 'searchResEntry', 'dn': 'CN=Alice'}])
        client = self.make_client(conn)
        dn, changed = ad_ldap_user.change_password(self.make_module(unlock=True), client)
        self.assertEqual((dn, changed), ('CN=Alice', True))
        self.assertEqual(conn.modify_calls[0][:3], ('CN=Alice', 'New-Secret-1', None))
        self.assertEqual(conn.unlocked, ['CN=Alice'])
        client.unbind.assert_called_once_with(conn)

    def test_change_mode_requires_and_sends_old_password(self):
        conn = FakeConnection(response=[{'type': 'searchResEntry', 'dn': 'CN=Alice'}])
        with self.assertRaises(ad_ldap.ADLdapError):
            ad_ldap_user.change_password(self.make_module(mode='change'), self.make_client(conn))

        module = self.make_module(mode='change', old_password='Old-Secret', unlock=True)
        ad_ldap_user.change_password(module, self.make_client(conn))
        self.assertEqual(conn.modify_calls[0][2], 'Old-Secret')
        self.assertEqual(conn.unlocked, [])

    def rejected_conn(self, result):
        return FakeConnection(response=[{'type': 'searchResEntry', 'dn': 'CN=Alice'}],
                              modify_results=[result])

    def test_retry_is_accepted_only_when_new_password_works(self):
        rejected = {'result': 19, 'message': '0000052D: Constraint violation'}
        client = self.make_client(self.rejected_conn(rejected))
        _, changed = ad_ldap_user.change_password(
            self.make_module(enforce_password_history=True), client
        )
        self.assertTrue(changed)
        client.check_password.assert_called_once_with('CN=Alice', 'New-Secret-1')

        with self.assertRaises(ad_ldap.ADLdapError):
            ad_ldap_user.change_password(
                self.make_module(), self.make_client(self.rejected_conn(rejected), check_status='rejected')
            )

        access_denied = {'result': RESULT_INSUFFICIENT_ACCESS_RIGHTS, 'message': '00000005: SecErr'}
        client = self.make_client(self.rejected_conn(access_denied))
        with self.assertRaises(ad_ldap.ADLdapError):
            ad_ldap_user.change_password(self.make_module(), client)
        client.check_password.assert_not_called()

    def test_retry_requires_password_set_after_change_started(self):
        # A password replaced less than an hour ago still binds (OldPasswordAllowedPeriod):
        # reusing it must not be mistaken for an applied change.
        rejected = {'result': 19, 'message': '0000052D: Constraint violation'}
        client = self.make_client(self.rejected_conn(rejected), pwd_last_set=1_800_000_000 - 3600)
        with self.assertRaises(ad_ldap.ADLdapError) as ctx:
            ad_ldap_user.change_password(self.make_module(enforce_password_history=True), client)
        self.assertEqual(ctx.exception.reason_code, 'PASSWORD_POLICY_VIOLATION')
        client.check_password.assert_not_called()

        # A password replaced one minute before this record also still binds; on the
        # DC clock it predates the record, so it is not an applied change either.
        client = self.make_client(self.rejected_conn(rejected), pwd_last_set=1_800_000_000 - 60)
        with self.assertRaises(ad_ldap.ADLdapError):
            ad_ldap_user.change_password(self.make_module(enforce_password_history=True), client)

        # The DC clock runs 10 minutes behind: a change applied after the record started
        # carries an "earlier" pwdLastSet and must still be recognised.
        client = self.make_client(self.rejected_conn(rejected), pwd_last_set=1_800_000_000 - 600 + 30,
                                  server_time=1_800_000_200 - 600)
        self.assertTrue(ad_ldap_user.change_password(self.make_module(), client)[1])
        client = self.make_client(self.rejected_conn(rejected), pwd_last_set=1_800_000_000 - 600 - 60,
                                  server_time=1_800_000_200 - 600)
        with self.assertRaises(ad_ldap.ADLdapError):
            ad_ldap_user.change_password(self.make_module(), client)

        # Without the DC time, a five minute allowance is used.
        client = self.make_client(self.rejected_conn(rejected), pwd_last_set=1_800_000_000 - 120,
                                  server_time=None)
        self.assertTrue(ad_ldap_user.change_password(self.make_module(), client)[1])

        # Without a start time nothing proves the change was applied.
        client = self.make_client(self.rejected_conn(rejected))
        with self.assertRaises(ad_ldap.ADLdapError):
            ad_ldap_user.change_password(self.make_module(change_started_at=0), client)
        client.get_pwd_last_set.assert_not_called()

    def test_change_mode_retry_with_stale_old_password(self):
        stale = {'result': 19, 'message': "00000056: AtrErr: DSID-03190F80, #1"}
        client = self.make_client(self.rejected_conn(stale))
        module = self.make_module(mode='change', old_password='Old-Secret')
        self.assertTrue(ad_ldap_user.change_password(module, client)[1])

    def test_server_time_parsing(self):
        conn = FakeConnection(response=[{'type': 'searchResEntry', 'dn': '',
                                         'attributes': {'currentTime': ['20270115080000.0Z']}}])
        self.assertEqual(ad_ldap.ADLdapClient.get_server_time(conn), 1800000000.0)

    def test_pwd_last_set_filetime_conversion(self):
        conn = FakeConnection(response=[{'type': 'searchResEntry', 'dn': 'CN=Alice',
                                         'attributes': {'pwdLastSet': ['134377392860191280']}}])
        ts = ad_ldap.ADLdapClient.get_pwd_last_set(conn, 'CN=Alice')
        self.assertAlmostEqual(ts, 134377392860191280 / 1e7 - ad_ldap.FILETIME_EPOCH_OFFSET)
        conn = FakeConnection(response=[{'type': 'searchResEntry', 'dn': 'CN=Alice',
                                         'attributes': {'pwdLastSet': ['0']}}])
        self.assertIsNone(ad_ldap.ADLdapClient.get_pwd_last_set(conn, 'CN=Alice'))


class LdapProtocolWiringTests(SimpleTestCase):
    def test_ldap_protocol_is_available_for_windows_ad(self):
        self.assertIn(Protocol.ldap, Protocol.settings())
        self.assertEqual(Protocol.settings()[Protocol.ldap]['port'], 636)
        choices = DirectoryTypes._get_protocol_constrains()[DirectoryTypes.WINDOWS_AD]['choices']
        self.assertIn('ldap', choices)

    def test_ldap_runs_locally_and_exposes_tls_settings(self):
        protocol = SimpleNamespace(name='ldap', port=636, setting={
            'security': 'starttls', 'allow_invalid_cert': False,
            'tls_server_name': ' dc01.corp.test ', 'ca_cert': 'PEM{{x}}',
        })
        config = JMSInventory.fill_ansible_config({}, protocol)
        self.assertEqual(config['ansible_connection'], 'local')

        host = {'jms_asset': {'spec_info': {}}}
        JMSInventory.make_protocol_setting_vars(host, [protocol])
        asset = host['jms_asset']
        self.assertEqual(asset['ldap_security'], 'starttls')
        self.assertEqual(asset['ldap_tls_server_name'], 'dc01.corp.test')
        self.assertNotIn('{{x}}', asset['ldap_ca_cert'])

    def test_change_mode_requires_old_secret(self):
        def asset(tp, method):
            return SimpleNamespace(platform=SimpleNamespace(
                type=tp, automation=SimpleNamespace(change_secret_method=method),
            ))

        get_error = ChangeSecretManager.get_old_secret_required_error
        host = {'jms_asset': {}, 'params': {'use_current_password': True}}
        self.assertIsNotNone(get_error(asset('windows_ad', 'change_secret_by_ldap'), host))
        host = {'jms_asset': {}, 'params': {'use_current_password': False}}
        self.assertIsNone(get_error(asset('windows_ad', 'change_secret_by_ldap'), host))
        host = {'jms_asset': {}, 'params': {'use_current_password': True}}
        self.assertIsNone(get_error(asset('windows_ad', 'change_secret_ad_windows'), host))
        host = {'jms_asset': {'oracle_change_secret_with_old_password': True}}
        self.assertIsNotNone(get_error(asset('oracle', 'change_secret_oracle'), host))

    def test_ldap_inventory_carries_change_start_time(self):
        from datetime import datetime, timezone as tz
        manager = ChangeSecretManager.__new__(ChangeSecretManager)
        manager.record_map = {}
        record = SimpleNamespace(new_secret='New-1', old_secret='Old-1',
                                 date_created=datetime(2027, 1, 15, 8, 0, tzinfo=tz.utc))
        manager.get_or_create_record = mock.Mock(return_value=record)
        manager.handle_ssh_secret = mock.Mock(return_value=('New-1', None))
        manager.gen_inventory = mock.Mock(side_effect=lambda h, *a, **kw: dict(h, account={}))

        def run(method):
            asset = SimpleNamespace(id='a1', platform=SimpleNamespace(
                type='windows_ad', automation=SimpleNamespace(change_secret_method=method)))
            account_obj = SimpleNamespace(id='c1', secret_type='password')
            h, _ = manager.gen_account_inventory(account_obj, asset, {'name': 'h', 'jms_asset': {}, 'params': {}}, '/tmp')
            return h['account']

        # A new record's secret was never sent to AD: no "already applied" shortcut.
        self.assertNotIn('change_started_at', run('change_secret_by_ldap'))
        manager.record_map = {'a1-c1': 'record-1'}
        self.assertEqual(run('change_secret_by_ldap')['change_started_at'],
                         int(record.date_created.timestamp()))
        self.assertNotIn('change_started_at', run('change_secret_ad_windows'))
