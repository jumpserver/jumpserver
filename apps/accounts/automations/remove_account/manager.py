import os
from collections import defaultdict
from copy import deepcopy

from django.db.models import QuerySet

from accounts.const import AutomationTypes
from accounts.models import Account
from common.utils import get_logger
from ..base.manager import AccountBasePlaybookManager

logger = get_logger(__name__)


class RemoveAccountManager(AccountBasePlaybookManager):
    super_accounts = ['root', 'administrator']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_account_mapper = dict()
        self.host_accounts = defaultdict(list)
        snapshot_account = self.execution.snapshot.get('accounts', [])
        self.snapshot_asset_account_map = defaultdict(list)
        for account in snapshot_account:
            self.snapshot_asset_account_map[str(account['asset'])].append(account)

    def prepare_runtime_dir(self):
        path = super().prepare_runtime_dir()
        ansible_config_path = os.path.join(path, 'ansible.cfg')

        with open(ansible_config_path, 'w') as f:
            f.write('[ssh_connection]\n')
            f.write('ssh_args = -o ControlMaster=no -o ControlPersist=no\n')
        return path

    @classmethod
    def method_type(cls):
        return AutomationTypes.remove_account

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        if host.get('error'):
            return host

        inventory_hosts = []
        accounts_to_remove = self.snapshot_asset_account_map.get(str(asset.id), [])

        for account in accounts_to_remove:
            username = account.get('username')
            if not username or username.lower() in self.super_accounts:
                print("Super account can not be remove: ", username)
                continue
            h = deepcopy(host)
            h['name'] += '(' + username + ')'
            self.host_account_mapper[h['name']] = account
            h['account'] = {'username': username}
            inventory_hosts.append(h)
        return inventory_hosts

    def on_host_success(self, host, result):
        tuple_asset_gather_account = self.host_account_mapper.get(host)
        if not tuple_asset_gather_account:
            return
        asset, gather_account = tuple_asset_gather_account
        try:
            Account.objects.filter(
                asset_id=asset.id,
                username=gather_account.username
            ).delete()
            gather_account.delete()
        except Exception as e:
            print(f'\033[31m Delete account {gather_account.username} failed: {e} \033[0m\n')
