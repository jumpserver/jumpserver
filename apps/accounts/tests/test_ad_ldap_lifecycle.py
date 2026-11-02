from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase
from ldap3.core.results import (
    RESULT_ATTRIBUTE_OR_VALUE_EXISTS,
    RESULT_ENTRY_ALREADY_EXISTS,
    RESULT_INSUFFICIENT_ACCESS_RIGHTS,
    RESULT_NOT_ALLOWED_ON_NON_LEAF,
    RESULT_NO_SUCH_OBJECT,
    RESULT_SUCCESS,
)

from accounts.automations.gather_account.filter import GatherAccountsFilter
from accounts.automations.remove_account.manager import RemoveAccountManager
from libs.ansible.modules import ad_ldap_account
from libs.ansible.modules_utils import ad_ldap

OK = {'result': RESULT_SUCCESS}
# 2026-10-29T09:15:00Z as an AD FILETIME.
FILETIME = (int(datetime(2026, 10, 29, 9, 15, tzinfo=timezone.utc).timestamp())
            + ad_ldap.FILETIME_EPOCH_OFFSET) * 10 ** 7


class RecordingConnection:
    """Records add/modify/delete calls and replays canned results."""

    def __init__(self, results=None, pages=None, who_am_i='u:CORP\\svc'):
        self.results = list(results or [])
        self.pages = list(pages or [])
        self.calls = []
        self.result = OK
        self.response = []
        self.extend = SimpleNamespace(standard=SimpleNamespace(who_am_i=lambda: who_am_i))

    def _finish(self, call):
        self.calls.append(call)
        self.result = self.results.pop(0) if self.results else OK
        return self.result['result'] == RESULT_SUCCESS

    def add(self, dn, attributes=None):
        return self._finish(('add', dn, attributes))

    def modify(self, dn, changes):
        return self._finish(('modify', dn, changes))

    def delete(self, dn):
        return self._finish(('delete', dn))

    def search(self, search_base, search_filter, **kwargs):
        self.calls.append(('search', search_base, search_filter, kwargs))
        entries, cookie, result = self.pages.pop(0)
        self.response = [{'type': 'searchResEntry', **e} for e in entries]
        self.result = dict(result, controls={ad_ldap.PAGED_RESULTS_OID: {'value': {'cookie': cookie}}})
        return result['result'] == RESULT_SUCCESS


class LifecycleHelperTests(SimpleTestCase):
    def test_user_identity(self):
        self.assertEqual(ad_ldap.user_identity('alice', 'corp.example.com'),
                         ('alice', 'alice@corp.example.com'))
        self.assertEqual(ad_ldap.user_identity('alice@corp.example.com'),
                         ('alice', 'alice@corp.example.com'))
        self.assertEqual(ad_ldap.user_identity('CORP\\alice', 'corp.example.com'),
                         ('alice', 'alice@corp.example.com'))
        self.assertEqual(ad_ldap.user_identity('alice'), ('alice', None))

    def test_sam_account_name_validation(self):
        ad_ldap.validate_sam_account_name('svc.app-01_x')
        for name in ('a' * 21, 'bad/name', 'a,b', 'a@b', 'trailing.', 'tab\tname', ''):
            with self.assertRaises(ad_ldap.ADLdapError, msg=name):
                ad_ldap.validate_sam_account_name(name)

    def test_filetime_conversion(self):
        self.assertEqual(ad_ldap.filetime_to_datetime(str(FILETIME)),
                         datetime(2026, 10, 29, 9, 15, tzinfo=timezone.utc))
        for value in (0, '0', None, '', ad_ldap.FILETIME_NEVER, 'garbage'):
            self.assertIsNone(ad_ldap.filetime_to_datetime(value), value)

    def test_rdn_value_unescapes_group_names(self):
        self.assertEqual(ad_ldap.rdn_value('CN=Ops\\, Prod,OU=Groups,DC=corp,DC=test'), 'Ops, Prod')
        self.assertEqual(ad_ldap.rdn_value('CN=\\E9quipe,DC=corp,DC=test'.replace('\\E9', '\\C3\\A9')), 'équipe')
        self.assertEqual(ad_ldap.rdn_value('CN=Domain Users,CN=Users,DC=corp,DC=test'), 'Domain Users')

    def test_protected_entry(self):
        self.assertTrue(ad_ldap.is_protected_entry({'adminCount': ['1']}))
        self.assertTrue(ad_ldap.is_protected_entry({'isCriticalSystemObject': ['TRUE']}))
        self.assertFalse(ad_ldap.is_protected_entry({'adminCount': ['0']}))
        self.assertFalse(ad_ldap.is_protected_entry({}))

    def test_entry_user_detail_matches_winrm_gather_record(self):
        detail = ad_ldap.entry_user_detail({'attributes': {
            'name': ['Alice'], 'sAMAccountName': ['alice'], 'userAccountControl': ['514'],
            'lastLogonTimestamp': [str(FILETIME)], 'pwdLastSet': [str(FILETIME)],
            'msDS-UserPasswordExpiryTimeComputed': [str(ad_ldap.FILETIME_NEVER)],
            'memberOf': ['CN=Staff,OU=G,DC=corp,DC=test', 'CN=Ops\\, Prod,DC=corp,DC=test'],
        }})
        self.assertEqual(detail, {
            'Name': 'Alice', 'SamAccountName': 'alice', 'Enabled': False,
            'LastLogonDate': '2026-10-29T09:15:00+00:00',
            'PasswordLastSet': '2026-10-29T09:15:00+00:00',
            'PasswordExpires': None,
            'GlobalGroupMemberships': ['Staff', 'Ops, Prod'],
        })
        minimal = ad_ldap.entry_user_detail({'attributes': {'sAMAccountName': 'bob', 'userAccountControl': '512'}})
        self.assertTrue(minimal['Enabled'])
        self.assertEqual(minimal['GlobalGroupMemberships'], [])
        self.assertIsNone(minimal['LastLogonDate'])


class LifecycleClientTests(SimpleTestCase):
    def test_create_user_single_add_with_password(self):
        conn = RecordingConnection()
        dn = ad_ldap.ADLdapClient.create_user(conn, 'OU=Staff,DC=corp,DC=test', 'alice',
                                              'alice@corp.test', 'Pw-1"x')
        self.assertEqual(dn, 'CN=alice,OU=Staff,DC=corp,DC=test')
        op, add_dn, attributes = conn.calls[0]
        self.assertEqual((op, add_dn), ('add', dn))
        self.assertEqual(attributes['unicodePwd'], '"Pw-1"x"'.encode('utf-16-le'))
        self.assertEqual(attributes['userAccountControl'], '512')
        self.assertEqual(attributes['userPrincipalName'], 'alice@corp.test')
        self.assertEqual(attributes['objectClass'][-1], 'user')

    def test_create_user_escapes_rdn_and_classifies_failures(self):
        conn = RecordingConnection()
        dn = ad_ldap.ADLdapClient.create_user(conn, 'OU=X,DC=c', '#lead', None, 'Pw-1')
        self.assertEqual(dn, 'CN=\\#lead,OU=X,DC=c')
        self.assertNotIn('userPrincipalName', conn.calls[0][2])
        cases = [
            ({'result': 19, 'message': '0000052D: Constraint violation'}, 'PASSWORD_POLICY_VIOLATION'),
            ({'result': RESULT_INSUFFICIENT_ACCESS_RIGHTS, 'message': '00000005: SecErr'}, 'INSUFFICIENT_ACCESS_RIGHTS'),
            ({'result': RESULT_ENTRY_ALREADY_EXISTS, 'message': '00000524: UpdErr'}, 'ACCOUNT_EXISTS'),
            # Logon name or UPN already used by a user outside the target OU.
            ({'result': 19, 'message': '000021C8: AtrErr: DSID-03200E96, #1:'}, 'ACCOUNT_EXISTS'),
            ({'result': RESULT_NO_SUCH_OBJECT, 'message': '0000208D: NameErr'}, 'OBJECT_NOT_FOUND'),
        ]
        for result, reason in cases:
            conn = RecordingConnection(results=[result])
            with self.assertRaises(ad_ldap.ADLdapError) as ctx:
                ad_ldap.ADLdapClient.create_user(conn, 'OU=X,DC=c', 'alice', None, 'Pw-1')
            self.assertEqual(ctx.exception.reason_code, reason)
        with self.assertRaises(ad_ldap.ADLdapError):
            ad_ldap.ADLdapClient.create_user(RecordingConnection(), 'OU=X,DC=c', 'x' * 21, None, 'Pw-1')

    def test_add_to_groups_keeps_existing_memberships(self):
        conn = RecordingConnection(results=[
            OK, {'result': RESULT_ENTRY_ALREADY_EXISTS}, {'result': RESULT_ATTRIBUTE_OR_VALUE_EXISTS},
        ])
        added = ad_ldap.ADLdapClient.add_to_groups(conn, 'CN=alice', ['CN=A', 'CN=B', 'CN=C'])
        self.assertEqual(added, ['CN=A'])
        self.assertEqual(conn.calls[0][2], {'member': [(ad_ldap.MODIFY_ADD, ['CN=alice'])]})
        conn = RecordingConnection(results=[{'result': RESULT_INSUFFICIENT_ACCESS_RIGHTS, 'message': ''}])
        with self.assertRaises(ad_ldap.ADLdapError) as ctx:
            ad_ldap.ADLdapClient.add_to_groups(conn, 'CN=alice', ['CN=Locked,DC=c'])
        self.assertEqual(ctx.exception.reason_code, 'INSUFFICIENT_ACCESS_RIGHTS')
        self.assertIn('Locked', str(ctx.exception))

    def test_disable_and_delete(self):
        conn = RecordingConnection()
        self.assertTrue(ad_ldap.ADLdapClient.disable_user(conn, 'CN=a', '66048'))
        self.assertEqual(conn.calls[0][2], {'userAccountControl': [(ad_ldap.MODIFY_REPLACE, ['66050'])]})
        conn = RecordingConnection()
        self.assertFalse(ad_ldap.ADLdapClient.disable_user(conn, 'CN=a', '514'))
        self.assertEqual(conn.calls, [])
        conn = RecordingConnection(results=[{'result': RESULT_NOT_ALLOWED_ON_NON_LEAF, 'message': ''}])
        with self.assertRaises(ad_ldap.ADLdapError) as ctx:
            ad_ldap.ADLdapClient.delete_user(conn, 'CN=a')
        self.assertEqual(ctx.exception.reason_code, 'NOT_LEAF')
        conn = RecordingConnection()
        ad_ldap.ADLdapClient.delete_user(conn, 'CN=a')
        self.assertEqual(conn.calls, [('delete', 'CN=a')])

    def test_search_users_follows_paging(self):
        conn = RecordingConnection(pages=[
            ([{'dn': 'CN=a', 'attributes': {}}, {'dn': 'CN=b', 'attributes': {}}], b'next', OK),
            ([{'dn': 'CN=c', 'attributes': {}}], b'', OK),
        ])
        entries = ad_ldap.ADLdapClient.search_users(conn, 'DC=c', page_size=2)
        self.assertEqual([e['dn'] for e in entries], ['CN=a', 'CN=b', 'CN=c'])
        self.assertIsNone(conn.calls[0][3]['paged_cookie'])
        self.assertEqual(conn.calls[1][3]['paged_cookie'], b'next')
        self.assertEqual(conn.calls[0][3]['paged_size'], 2)
        self.assertEqual(conn.calls[0][2], ad_ldap.USER_OBJECT_FILTER)

        conn = RecordingConnection(pages=[
            ([{'dn': 'CN=a', 'attributes': {}}], b'next', OK),
            ([], b'', {'result': RESULT_NO_SUCH_OBJECT, 'description': 'noSuchObject', 'message': ''}),
        ])
        with self.assertRaises(ad_ldap.ADLdapError) as ctx:
            ad_ldap.ADLdapClient.search_users(conn, 'OU=gone,DC=c')
        self.assertEqual(ctx.exception.reason_code, 'SEARCH_FAILED')

    def test_login_sam(self):
        for who, sam in (('u:CORP\\svc', 'svc'), ('u:svc@corp.test', 'svc'), ('', None)):
            self.assertEqual(ad_ldap.ADLdapClient.get_login_sam(RecordingConnection(who_am_i=who)), sam)
        broken = RecordingConnection()
        broken.extend.standard.who_am_i = mock.Mock(side_effect=RuntimeError('unsupported'))
        self.assertIsNone(ad_ldap.ADLdapClient.get_login_sam(broken))


class AccountModuleTests(SimpleTestCase):
    def make_module(self, check_mode=False, **params):
        defaults = {
            'login_user': 'svc@corp.test', 'login_password': 'svc-pw', 'name': 'alice',
            'password': 'New-Secret-1', 'state': 'present', 'ou': '', 'groups': '',
            'disable_only': False, 'domain_name': 'corp.test', 'search_base': '', 'verify': True,
        }
        defaults.update(params)
        return SimpleNamespace(params=defaults, check_mode=check_mode)

    def make_client(self, existing=None, groups=None, login_sam='svc'):
        client = ad_ldap.ADLdapClient('dc01', 636)
        client.bind = mock.Mock(return_value='conn')
        client.unbind = mock.Mock()
        if existing is None:
            client.find_user_entry = mock.Mock(side_effect=ad_ldap.ADLdapError('nf', 'USER_NOT_FOUND'))
        else:
            client.find_user_entry = mock.Mock(return_value=existing)
        groups = groups or {}

        def find_group(conn, name, base):
            if name not in groups:
                raise ad_ldap.ADLdapError('group not found', 'GROUP_NOT_FOUND')
            return groups[name]
        client.find_group = mock.Mock(side_effect=find_group)
        client.create_user = mock.Mock(side_effect=lambda conn, c, sam, upn, pw: 'CN=%s,%s' % (sam, c))
        client.set_password = mock.Mock()
        client.add_to_groups = mock.Mock(side_effect=lambda conn, dn, gs: list(gs))
        client.disable_user = mock.Mock(return_value=True)
        client.delete_user = mock.Mock()
        client.get_login_sam = mock.Mock(return_value=login_sam)
        return client

    def test_push_creates_missing_user_in_ou_with_groups(self):
        client = self.make_client(groups={'Staff': 'CN=Staff,DC=corp,DC=test'})
        module = self.make_module(ou='OU=Staff,DC=corp,DC=test', groups='Staff')
        data, changed = ad_ldap_account.push_account(module, client)
        self.assertTrue(changed)
        self.assertEqual(data['action'], 'created')
        client.create_user.assert_called_once_with(
            'conn', 'OU=Staff,DC=corp,DC=test', 'alice', 'alice@corp.test', 'New-Secret-1')
        # Lookups of existing users are limited to the target OU.
        self.assertEqual(client.find_user_entry.call_args.kwargs['search_base'], 'OU=Staff,DC=corp,DC=test')
        client.find_group.assert_called_once_with('conn', 'Staff', 'DC=corp,DC=test')
        self.assertEqual(data['groups_added'], ['CN=Staff,DC=corp,DC=test'])
        client.set_password.assert_not_called()

    def test_push_defaults_to_users_container_and_resets_existing(self):
        client = self.make_client()
        data, _ = ad_ldap_account.push_account(self.make_module(), client)
        self.assertEqual(data['user_dn'], 'CN=alice,CN=Users,DC=corp,DC=test')
        self.assertEqual(client.find_user_entry.call_args.kwargs['search_base'], '')

        client = self.make_client(existing={'dn': 'CN=alice,OU=X,DC=corp,DC=test', 'attributes': {}})
        data, changed = ad_ldap_account.push_account(self.make_module(), client)
        self.assertEqual((data['action'], changed), ('updated', True))
        client.set_password.assert_called_once_with('conn', 'CN=alice,OU=X,DC=corp,DC=test', 'New-Secret-1')
        client.create_user.assert_not_called()

    def test_push_resolves_groups_before_any_change(self):
        client = self.make_client(groups={'Staff': 'CN=Staff'})
        with self.assertRaises(ad_ldap.ADLdapError) as ctx:
            ad_ldap_account.push_account(self.make_module(groups='Staff, Missing'), client)
        self.assertEqual(ctx.exception.reason_code, 'GROUP_NOT_FOUND')
        client.create_user.assert_not_called()
        client.set_password.assert_not_called()
        client.unbind.assert_called_once()

    def test_push_requires_password_and_container(self):
        with self.assertRaises(ad_ldap.ADLdapError):
            ad_ldap_account.push_account(self.make_module(password=''), self.make_client())
        with self.assertRaises(ad_ldap.ADLdapError) as ctx:
            ad_ldap_account.push_account(self.make_module(domain_name=''), self.make_client())
        self.assertEqual(ctx.exception.reason_code, 'OU_REQUIRED')

    def test_push_check_mode_changes_nothing(self):
        client = self.make_client()
        data, changed = ad_ldap_account.push_account(self.make_module(check_mode=True), client)
        self.assertFalse(changed)
        self.assertEqual(data['action'], 'created')
        client.create_user.assert_not_called()

    def test_remove_deletes_or_disables(self):
        entry = {'dn': 'CN=alice,OU=X', 'attributes': {'sAMAccountName': ['alice'], 'userAccountControl': ['512']}}
        client = self.make_client(existing=entry)
        data, changed = ad_ldap_account.remove_account(self.make_module(state='absent'), client)
        self.assertEqual((data['action'], changed), ('deleted', True))
        client.delete_user.assert_called_once_with('conn', 'CN=alice,OU=X')
        self.assertEqual(client.find_user_entry.call_args.kwargs['attributes'], ad_ldap.PROTECTION_ATTRIBUTES)

        client = self.make_client(existing=entry)
        data, changed = ad_ldap_account.remove_account(
            self.make_module(state='absent', disable_only=True), client)
        self.assertEqual((data['action'], changed), ('disabled', True))
        client.disable_user.assert_called_once_with('conn', 'CN=alice,OU=X', '512')
        client.delete_user.assert_not_called()

    def test_remove_missing_user_is_a_no_op(self):
        client = self.make_client()
        data, changed = ad_ldap_account.remove_account(self.make_module(state='absent'), client)
        self.assertEqual((data['action'], changed), ('absent', False))
        client.delete_user.assert_not_called()

    def test_remove_refuses_protected_and_login_accounts(self):
        for attributes in ({'sAMAccountName': ['admin'], 'adminCount': ['1']},
                           {'sAMAccountName': ['krbtgt'], 'isCriticalSystemObject': ['TRUE']}):
            client = self.make_client(existing={'dn': 'CN=x', 'attributes': attributes})
            with self.assertRaises(ad_ldap.ADLdapError) as ctx:
                ad_ldap_account.remove_account(self.make_module(state='absent', name='x'), client)
            self.assertEqual(ctx.exception.reason_code, 'PROTECTED_ACCOUNT')
            client.delete_user.assert_not_called()
            client.disable_user.assert_not_called()

        client = self.make_client(existing={'dn': 'CN=svc', 'attributes': {'sAMAccountName': ['SVC']}})
        with self.assertRaises(ad_ldap.ADLdapError) as ctx:
            ad_ldap_account.remove_account(self.make_module(state='absent', name='svc'), client)
        self.assertEqual(ctx.exception.reason_code, 'LOGIN_ACCOUNT')

        # Without Who Am I the login user name is used.
        client = self.make_client(existing={'dn': 'CN=svc', 'attributes': {'sAMAccountName': ['svc']}},
                                  login_sam=None)
        with self.assertRaises(ad_ldap.ADLdapError):
            ad_ldap_account.remove_account(self.make_module(state='absent', name='svc'), client)
        client.delete_user.assert_not_called()


class GatherAndRemoveWiringTests(SimpleTestCase):
    methods = {
        'gather_accounts_windows_ad': {'method': 'gather_accounts', 'type': ['windows_ad']},
        'gather_accounts_by_ldap': {'method': 'gather_accounts', 'type': ['windows_ad']},
    }
    info = {'user_details': [{
        'SamAccountName': 'alice', 'PasswordLastSet': '2026-10-29T09:15:00+00:00',
        'PasswordExpires': None, 'LastLogonDate': None, 'GlobalGroupMemberships': ['Staff'],
    }]}

    def test_configured_gather_method_selects_the_filter(self):
        for method_id in self.methods:
            result = GatherAccountsFilter('windows_ad').run(self.methods, self.info, method_id=method_id)
            self.assertEqual(result['alice']['groups'], ['Staff'])
            self.assertEqual(result['alice']['detail'], {'groups': ['Staff']})
            self.assertEqual(result['alice']['date_password_change'],
                             datetime(2026, 10, 29, 9, 15, tzinfo=timezone.utc))

    def test_unknown_method_keeps_legacy_selection(self):
        with mock.patch.object(GatherAccountsFilter, 'by_ldap_filter', return_value='ldap'), \
                mock.patch.object(GatherAccountsFilter, 'windows_ad_filter', return_value='winrm'):
            run = GatherAccountsFilter('windows_ad').run
            self.assertEqual(run(self.methods, self.info, method_id='gather_accounts_windows_ad'), 'winrm')
            self.assertEqual(run(self.methods, self.info, method_id='gather_accounts_by_ldap'), 'ldap')
            # Legacy behaviour: the last method of the type wins.
            self.assertEqual(run(self.methods, self.info), 'ldap')
            self.assertEqual(run(self.methods, self.info, method_id='missing'), 'ldap')

    def test_ldap_gather_output_is_parsed_like_winrm(self):
        entry = {'attributes': {'sAMAccountName': ['alice'], 'userAccountControl': ['512'],
                                'pwdLastSet': [str(FILETIME)], 'memberOf': ['CN=Staff,DC=c']}}
        info = {'user_details': [ad_ldap.entry_user_detail(entry)]}
        ldap = GatherAccountsFilter('windows_ad').run(self.methods, info, method_id='gather_accounts_by_ldap')
        winrm = GatherAccountsFilter('windows_ad').run(self.methods, self.info, method_id='gather_accounts_windows_ad')
        self.assertEqual(ldap, winrm)

    def test_unchanged_groups_are_not_reported_as_changed(self):
        from accounts.automations.gather_account.manager import get_items_diff
        gathered = GatherAccountsFilter('windows_ad').run(
            self.methods, self.info, method_id='gather_accounts_by_ldap')['alice']
        stored = SimpleNamespace(**{k: v for k, v in gathered.items() if k != 'groups'})
        self.assertNotIn('groups', get_items_diff(stored, dict(gathered)))
        changed = dict(gathered, groups=['Staff', 'Ops'], detail={'groups': ['Staff', 'Ops']})
        stored = SimpleNamespace(**{k: v for k, v in gathered.items() if k != 'groups'})
        self.assertIn('groups', get_items_diff(stored, changed))

    def test_directory_service_login_account_is_protected(self):
        ds = SimpleNamespace(is_dir_svc=lambda: True)
        host = SimpleNamespace(is_dir_svc=lambda: False)
        check = RemoveAccountManager.is_connection_account
        self.assertTrue(check(ds, 'ldapsvc', 'ldapsvc@corp.test'))
        self.assertTrue(check(ds, 'CORP\\LdapSvc', 'ldapsvc@corp.test'))
        self.assertFalse(check(ds, 'alice', 'ldapsvc@corp.test'))
        self.assertTrue(check(host, 'root', 'ROOT'))
        self.assertFalse(check(host, 'app', 'app@%'))
