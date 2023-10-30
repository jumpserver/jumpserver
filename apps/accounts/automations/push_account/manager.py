from accounts.const import AutomationTypes
from common.utils import get_logger
from ..base.manager import AccountBasePlaybookManager
from ..change_secret.manager import ChangeSecretManager

logger = get_logger(__name__)


class PushAccountManager(ChangeSecretManager, AccountBasePlaybookManager):

    @classmethod
    def method_type(cls):
        return AutomationTypes.push_account

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
