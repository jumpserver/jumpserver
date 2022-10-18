from collections import defaultdict
from assets.models import Account
from .permission import AssetPermissionUtil


class PermAccountUtil(AssetPermissionUtil):
    """ 资产授权账号相关的工具 """

    def get_user_perm_asset_accounts(self, user, asset, with_actions=False):
        """ 获取授权给用户某个资产的账号 """
        perms = self.get_permissions_for_user_asset(user, asset)
        accounts = self.get_permissions_accounts(perms, with_actions=with_actions)
        return accounts

    def get_user_perm_accounts(self, user, with_actions=False):
        """ 获取授权给用户的所有账号 """
        perms = self.get_permissions_for_user(user)
        accounts = self.get_permissions_accounts(perms, with_actions=with_actions)
        return accounts

    @staticmethod
    def get_permissions_accounts(permissions, with_actions=False):
        aid_actions_map = defaultdict(int)
        for perm in permissions:
            account_ids = perm.get_all_accounts(flat=True)
            actions = perm.actions
            for aid in account_ids:
                aid_actions_map[str(aid)] |= actions
        account_ids = list(aid_actions_map.keys())
        accounts = Account.objects.filter(id__in=account_ids)
        if with_actions:
            for account in accounts:
                account.actions = aid_actions_map.get(str(account.id))
        return accounts

