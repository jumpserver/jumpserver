import os
from copy import deepcopy

from django.db.models import QuerySet

from accounts.const import AutomationTypes, Connectivity, SecretType
from common.utils import get_logger
from ..base.manager import AccountBasePlaybookManager

logger = get_logger(__name__)


class VerifyAccountManager(AccountBasePlaybookManager):

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
        return AutomationTypes.verify_account

    def get_accounts(self, privilege_account, accounts: QuerySet):
        account_ids = self.execution.snapshot['accounts']
        accounts = accounts.filter(id__in=account_ids)
        return accounts

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        host = super().host_callback(
            host, asset=asset, account=account,
            automation=automation, path_dir=path_dir, **kwargs
        )
        if host.get('error'):
            return host

        accounts = asset.accounts.all()
        accounts = self.get_accounts(account, accounts)
        inventory_hosts = []

        for account in accounts:
            h = deepcopy(host)
            h['name'] += '(' + account.username + ')'
            self.host_account_mapper[h['name']] = account
            secret = account.secret
            if secret is None:
                print(f'account {account.name} secret is None')
                continue

            private_key_path = None
            if account.secret_type == SecretType.SSH_KEY:
                private_key_path = self.generate_private_key_path(secret, path_dir)
                secret = self.generate_public_key(secret)

            h['secret_type'] = account.secret_type
            h['account'] = {
                'name': account.name,
                'username': account.username,
                'secret_type': account.secret_type,
                'secret': account.escape_jinja2_syntax(secret),
                'private_key_path': private_key_path,
                'become': account.get_ansible_become_auth(),
            }
            if account.platform.type == 'oracle':
                h['account']['mode'] = 'sysdba' if account.privileged else None
            inventory_hosts.append(h)
        return inventory_hosts

    def on_host_success(self, host, result):
        account = self.host_account_mapper.get(host)
        account.set_connectivity(Connectivity.OK)

    def on_host_error(self, host, error, result):
        account = self.host_account_mapper.get(host)
        account.set_connectivity(Connectivity.ERR)
