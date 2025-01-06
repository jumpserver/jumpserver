from copy import deepcopy

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from accounts.automations.methods import platform_automation_methods
from accounts.const import SSHKeyStrategy, SecretStrategy, SecretType
from accounts.models import BaseAccountQuerySet
from assets.automations.base.manager import BasePlaybookManager
from assets.const import HostTypes
from common.utils import get_logger

logger = get_logger(__name__)


class AccountBasePlaybookManager(BasePlaybookManager):
    template_path = ''

    @property
    def platform_automation_methods(self):
        return platform_automation_methods


class BaseChangeSecretPushManager(AccountBasePlaybookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secret_type = self.execution.snapshot.get('secret_type')
        self.secret_strategy = self.execution.snapshot.get(
            'secret_strategy', SecretStrategy.custom
        )
        self.ssh_key_change_strategy = self.execution.snapshot.get(
            'ssh_key_change_strategy', SSHKeyStrategy.set_jms
        )
        self.account_ids = self.execution.snapshot['accounts']

    def gen_account_inventory(self, account, asset, h, path_dir):
        raise NotImplementedError

    def get_ssh_params(self, secret, secret_type):
        kwargs = {}
        if secret_type != SecretType.SSH_KEY:
            return kwargs
        kwargs['strategy'] = self.ssh_key_change_strategy
        kwargs['exclusive'] = 'yes' if kwargs['strategy'] == SSHKeyStrategy.set else 'no'

        if kwargs['strategy'] == SSHKeyStrategy.set_jms:
            kwargs['regexp'] = '.*{}$'.format(secret.split()[2].strip())
        return kwargs

    def get_accounts(self, privilege_account) -> BaseAccountQuerySet | None:
        if not privilege_account:
            print('Not privilege account')
            return

        asset = privilege_account.asset
        accounts = asset.accounts.all()
        accounts = accounts.filter(id__in=self.account_ids, secret_reset=True)

        if self.secret_type:
            accounts = accounts.filter(secret_type=self.secret_type)

        if settings.CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED:
            accounts = accounts.filter(privileged=False).exclude(
                username__in=['root', 'administrator', privilege_account.username]
            )
        return accounts

    def handle_ssh_secret(self, secret_type, new_secret, path_dir):
        private_key_path = None
        if secret_type == SecretType.SSH_KEY:
            private_key_path = self.generate_private_key_path(new_secret, path_dir)
            new_secret = self.generate_public_key(new_secret)
        return new_secret, private_key_path

    def gen_inventory(self, h, account, new_secret, private_key_path, asset):
        secret_type = account.secret_type
        h['ssh_params'].update(self.get_ssh_params(new_secret, secret_type))
        h['account'] = {
            'name': account.name,
            'username': account.username,
            'secret_type': secret_type,
            'secret': account.escape_jinja2_syntax(new_secret),
            'private_key_path': private_key_path,
            'become': account.get_ansible_become_auth(),
        }
        if asset.platform.type == 'oracle':
            h['account']['mode'] = 'sysdba' if account.privileged else None
        return h

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        host = super().host_callback(
            host, asset=asset, account=account, automation=automation,
            path_dir=path_dir, **kwargs
        )
        if host.get('error'):
            return host

        host['check_conn_after_change'] = self.execution.snapshot.get('check_conn_after_change', True)
        host['ssh_params'] = {}

        accounts = self.get_accounts(account)
        error_msg = _("No pending accounts found")
        if not accounts:
            print(f'{asset}: {error_msg}')
            return []

        if asset.type == HostTypes.WINDOWS:
            accounts = accounts.filter(secret_type=SecretType.PASSWORD)

        inventory_hosts = []
        if asset.type == HostTypes.WINDOWS and self.secret_type == SecretType.SSH_KEY:
            print(f'Windows {asset} does not support ssh key push')
            return inventory_hosts

        for account in accounts:
            h = deepcopy(host)
            h['name'] += '(' + account.username + ')'  # To distinguish different accounts
            h = self.gen_account_inventory(account, asset, h, path_dir)
            inventory_hosts.append(h)

        return inventory_hosts
