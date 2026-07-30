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
        self.account_ids = set(map(
            str, self.execution.snapshot.get('accounts', [])
        ))
        self.found_account_ids = set()

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
        accounts = accounts.filter(id__in=self.account_ids)
        return accounts

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        host = super().host_callback(
            host, asset=asset, account=account,
            automation=automation, path_dir=path_dir, **kwargs
        )
        if host.get('error'):
            return host

        accounts = asset.all_accounts.all()
        accounts = self.get_accounts(account, accounts)
        inventory_hosts = []

        for account in accounts:
            self.found_account_ids.add(str(account.id))
            h = deepcopy(host)
            h['name'] += '(' + account.username + ')'
            self.host_account_mapper[h['name']] = account
            secret = account.secret
            if not secret:
                print(f'account {account.name} secret is None')
                h['error'] = 'Account secret is empty'
                inventory_hosts.append(h)
                continue

            private_key_path = None
            if account.secret_type == SecretType.SSH_KEY:
                private_key_path = self.generate_private_key_path(secret, path_dir)
                secret = self.generate_public_key(secret)

            h['secret_type'] = account.secret_type
            h['account'] = {
                'name': account.name,
                'username': account.username,
                'full_username': account.full_username,
                'secret_type': account.secret_type,
                'secret': account.escape_jinja2_syntax(secret),
                'private_key_path': private_key_path,
                'become': account.get_ansible_become_auth(),
            }
            if account.platform.type == 'oracle':
                use_sysdba = (
                    account.privileged and
                    h['jms_asset'].get('oracle_sysdba', False)
                )
                h['account']['mode'] = 'sysdba' if use_sysdba else None
            inventory_hosts.append(h)
        return inventory_hosts

    def get_runners(self):
        runners = super().get_runners()
        for account_id in sorted(
                self.account_ids - self.found_account_ids
        ):
            super().on_inventory_host_error(
                account_id, 'Account not found or inactive'
            )
        return runners

    def on_host_success(self, host, result):
        account = self.host_account_mapper.get(host)
        if not account:
            return super().on_host_error(
                host, 'Account mapping not found', result
            )
        try:
            account.set_connectivity(Connectivity.OK)
        except Exception as e:
            super().on_host_error(host, str(e), result)
            print(
                f'\033[31m Update account '
                f'{getattr(account, "name", "-")} connectivity failed: '
                f'{e} \033[0m\n'
            )
            return
        super().on_host_success(host, result)

    def on_host_error(self, host, error, result):
        super().on_host_error(host, error, result)
        account = self.host_account_mapper.get(host)
        if not account:
            return
        try:
            error_tp = account.get_err_connectivity(error)
            account.set_connectivity(error_tp)
        except Exception as e:
            print(
                f'\033[31m Update account '
                f'{getattr(account, "name", "-")} connectivity failed: '
                f'{e} \033[0m\n'
            )
