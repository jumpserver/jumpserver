from copy import deepcopy

from common.utils import get_logger
from accounts.const import AutomationTypes, SecretType
from assets.automations.base.manager import BasePlaybookManager
from accounts.automations.methods import platform_automation_methods

logger = get_logger(__name__)


class PushOrVerifyHostCallbackMixin:
    execution: callable
    get_accounts: callable
    host_account_mapper: dict
    generate_public_key: callable
    generate_private_key_path: callable

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        host = super().host_callback(host, asset=asset, account=account, automation=automation, **kwargs)
        if host.get('error'):
            return host

        accounts = asset.accounts.all()
        accounts = self.get_accounts(account, accounts)

        inventory_hosts = []
        for account in accounts:
            h = deepcopy(host)
            h['name'] += '_' + account.username
            self.host_account_mapper[h['name']] = account
            secret = account.secret

            private_key_path = None
            if account.secret_type == SecretType.SSH_KEY:
                private_key_path = self.generate_private_key_path(secret, path_dir)
                secret = self.generate_public_key(secret)

            h['secret_type'] = account.secret_type
            h['account'] = {
                'name': account.name,
                'username': account.username,
                'secret_type': account.secret_type,
                'secret': secret,
                'private_key_path': private_key_path
            }
            inventory_hosts.append(h)
        return inventory_hosts


class AccountBasePlaybookManager(BasePlaybookManager):
    pass

    @property
    def platform_automation_methods(self):
        return platform_automation_methods
