from copy import deepcopy

from accounts.const import AutomationTypes, SecretType, Connectivity
from assets.const import HostTypes
from common.utils import get_logger
from ..base.manager import AccountBasePlaybookManager
from ..change_secret.manager import ChangeSecretManager

logger = get_logger(__name__)


class PushAccountManager(ChangeSecretManager, AccountBasePlaybookManager):
    ansible_account_prefer = ''

    @classmethod
    def method_type(cls):
        return AutomationTypes.push_account

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        host = super(ChangeSecretManager, self).host_callback(
            host, asset=asset, account=account, automation=automation,
            path_dir=path_dir, **kwargs
        )
        if host.get('error'):
            return host

        accounts = self.get_accounts(account)
        inventory_hosts = []
        if asset.type == HostTypes.WINDOWS and self.secret_type == SecretType.SSH_KEY:
            msg = f'Windows {asset} does not support ssh key push'
            print(msg)
            return inventory_hosts

        host['ssh_params'] = {}
        for account in accounts:
            h = deepcopy(host)
            secret_type = account.secret_type
            h['name'] += '(' + account.username + ')'
            if self.secret_type is None:
                new_secret = account.secret
            else:
                new_secret = self.get_secret(secret_type)

            self.name_recorder_mapper[h['name']] = {
                'account': account, 'new_secret': new_secret,
            }

            private_key_path = None
            if secret_type == SecretType.SSH_KEY:
                private_key_path = self.generate_private_key_path(new_secret, path_dir)
                new_secret = self.generate_public_key(new_secret)

            h['ssh_params'].update(self.get_ssh_params(account, new_secret, secret_type))
            h['account'] = {
                'name': account.name,
                'username': account.username,
                'secret_type': secret_type,
                'secret': new_secret,
                'private_key_path': private_key_path,
                'become': account.get_ansible_become_auth(),
            }
            if asset.platform.type == 'oracle':
                h['account']['mode'] = 'sysdba' if account.privileged else None
            inventory_hosts.append(h)
        return inventory_hosts

    def on_host_success(self, host, result):
        account_info = self.name_recorder_mapper.get(host)
        if not account_info:
            return

        account = account_info['account']
        new_secret = account_info['new_secret']
        if not account:
            return
        account.secret = new_secret
        account.save(update_fields=['secret'])
        account.set_connectivity(Connectivity.OK)

    def on_host_error(self, host, error, result):
        pass

    def on_runner_failed(self, runner, e):
        logger.error("Pust account error: {}".format(e))

    def run(self, *args, **kwargs):
        if self.secret_type and not self.check_secret():
            return
        super(ChangeSecretManager, self).run(*args, **kwargs)

    # @classmethod
    # def trigger_by_asset_create(cls, asset):
    #     automations = PushAccountAutomation.objects.filter(
    #         triggers__contains=TriggerChoice.on_asset_create
    #     )
    #     account_automation_map = {auto.username: auto for auto in automations}
    #
    #     util = AssetPermissionUtil()
    #     permissions = util.get_permissions_for_assets([asset], with_node=True)
    #     account_permission_map = defaultdict(list)
    #     for permission in permissions:
    #         for account in permission.accounts:
    #             account_permission_map[account].append(permission)
    #
    #     username_automation_map = {}
    #     for username, automation in account_automation_map.items():
    #         if username != '@USER':
    #             username_automation_map[username] = automation
    #             continue
    #
    #         asset_permissions = account_permission_map.get(username)
    #         if not asset_permissions:
    #             continue
    #         asset_permissions = util.get_permissions([p.id for p in asset_permissions])
    #         usernames = asset_permissions.values_list('users__username', flat=True).distinct()
    #         for _username in usernames:
    #             username_automation_map[_username] = automation
    #
    #     asset_usernames_exists = asset.accounts.values_list('username', flat=True)
    #     accounts_to_create = []
    #     accounts_to_push = []
    #     for username, automation in username_automation_map.items():
    #         if username in asset_usernames_exists:
    #             continue
    #
    #         if automation.secret_strategy != SecretStrategy.custom:
    #             secret_generator = SecretGenerator(
    #                 automation.secret_strategy, automation.secret_type,
    #                 automation.password_rules
    #             )
    #             secret = secret_generator.get_secret()
    #         else:
    #             secret = automation.secret
    #
    #         account = Account(
    #             username=username, secret=secret,
    #             asset=asset, secret_type=automation.secret_type,
    #             comment='Create by account creation {}'.format(automation.name),
    #         )
    #         accounts_to_create.append(account)
    #         if automation.action == 'create_and_push':
    #             accounts_to_push.append(account)
    #         else:
    #             accounts_to_create.append(account)
    #
    #         logger.debug(f'Create account {account} for asset {asset}')

    # @classmethod
    # def trigger_by_permission_accounts_change(cls):
    #     pass
