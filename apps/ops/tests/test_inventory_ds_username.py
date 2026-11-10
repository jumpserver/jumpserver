from django.test import SimpleTestCase

from accounts.automations.verify_account.manager import PersonalCredentialAccount
from accounts.models import Account, PersonalAssetCredential
from assets.models import Asset, DirectoryService, Platform
from ops.ansible.inventory import JMSInventory
from ops.ansible.utils import escape_jinja2_syntax


def make_asset(name, category='host', tp='linux', domain_name=None):
    platform = Platform(name=name, category=category, type=tp, su_enabled=True, su_method='sudo')
    asset = Asset(name=name, platform=platform)
    if domain_name is not None:
        asset.ds = DirectoryService(domain_name=domain_name)
    return asset


class DirectoryServiceUsernameTests(SimpleTestCase):
    def setUp(self):
        self.linux = make_asset('linux01')
        self.windows = make_asset('win01', tp='windows')
        self.ad = make_asset('corp-ad', category='ds', tp='windows_ad', domain_name='corp.example.com')

    def test_directory_service_account_logs_in_to_linux_with_upn(self):
        account = Account(username='aduser', asset=self.ad)
        self.assertEqual(JMSInventory.get_username(self.linux, account), 'aduser@corp.example.com')

    def test_local_and_domain_qualified_usernames_are_unchanged(self):
        root = Account(username='root', asset=self.linux)
        self.assertEqual(JMSInventory.get_username(self.linux, root), 'root')
        for username in ('aduser@corp.example.com', 'CORP\\aduser'):
            with self.subTest(username=username):
                account = Account(username=username, asset=self.ad)
                self.assertEqual(JMSInventory.get_username(self.linux, account), username)

    def test_personal_credential_username_is_used_as_saved(self):
        for asset in (self.linux, self.windows):
            for username in ('root', 'aduser@corp.example.com'):
                with self.subTest(asset=asset.name, username=username):
                    credential = PersonalAssetCredential(username=username, protocol='ssh', asset=asset)
                    account = PersonalCredentialAccount(credential)
                    self.assertEqual(JMSInventory.get_username(asset, account), username)

    def test_su_from_directory_service_login_user_is_escaped(self):
        ad = make_asset('evil-ad', category='ds', tp='windows_ad', domain_name='example.com{{ 6 * 7 }}')
        login = Account(username='aduser', secret_type='password', secret='login-password', asset=ad)
        root = Account(username='root', secret_type='password', secret='root-password',
                       asset=self.linux, su_from=login)
        expected = escape_jinja2_syntax('aduser@example.com{{ 6 * 7 }}')
        self.assertNotEqual(expected, 'aduser@example.com{{ 6 * 7 }}')
        auth = root.get_ansible_become_auth()
        self.assertEqual(auth['ansible_user'], expected)
        self.assertEqual(auth['ansible_become_user'], 'root')
        custom = JMSInventory.make_custom_become_ansible_vars(root, auth, None)
        self.assertEqual(custom['jms_custom_become_user'], expected)
