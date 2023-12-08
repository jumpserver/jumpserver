import os
from copy import deepcopy

from django.db.models import QuerySet

from accounts.const import AutomationTypes
from accounts.models import Account
from common.utils import get_logger
from ..base.manager import AccountBasePlaybookManager

logger = get_logger(__name__)


class RemoveAccountManager(AccountBasePlaybookManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_account_mapper = {}

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

    def get_gather_accounts(self, privilege_account, gather_accounts: QuerySet):
        gather_account_ids = self.execution.snapshot['gather_accounts']
        gather_accounts = gather_accounts.filter(id__in=gather_account_ids)
        gather_accounts = gather_accounts.exclude(
            username__in=[privilege_account.username, 'root', 'Administrator']
        )
        return gather_accounts

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        if host.get('error'):
            return host

        gather_accounts = asset.gatheredaccount_set.all()
        gather_accounts = self.get_gather_accounts(account, gather_accounts)

        inventory_hosts = []

        for gather_account in gather_accounts:
            h = deepcopy(host)
            h['name'] += '(' + gather_account.username + ')'
            self.host_account_mapper[h['name']] = (asset, gather_account)
            h['account'] = {'username': gather_account.username}
            inventory_hosts.append(h)
        return inventory_hosts

    def on_host_success(self, host, result):
        tuple_asset_gather_account = self.host_account_mapper.get(host)
        if not tuple_asset_gather_account:
            return
        asset, gather_account = tuple_asset_gather_account
        Account.objects.filter(
            asset_id=asset.id,
            username=gather_account.username
        ).delete()
        gather_account.delete()
