import time
from collections import defaultdict
from assets.models import Account
from .permission import AssetPermissionUtil

__all__ = ['PermAccountUtil']


class PermAccountUtil(AssetPermissionUtil):
    """ 资产授权账号相关的工具 """

    def get_perm_accounts_for_user(self, user, with_actions=False):
        """ 获取授权给用户的所有账号 """
        perms = self.get_permissions_for_user(user)
        accounts = self.get_perm_accounts_for_permissions(perms, with_actions=with_actions)
        return accounts

    def get_perm_accounts_for_user_asset(self, user, asset, with_actions=False, with_perms=False):
        """ 获取授权给用户某个资产的账号 """
        perms = self.get_permissions_for_user_asset(user, asset)
        accounts = self.get_perm_accounts_for_permissions(perms, with_actions=with_actions)
        if with_perms:
            return perms, accounts
        return accounts

    def get_perm_accounts_for_user_group_asset(self, user_group, asset, with_actions=False):
        """ 获取授权给用户组某个资产的账号 """
        perms = self.get_permissions_for_user_group_asset(user_group, asset)
        accounts = self.get_perm_accounts_for_permissions(perms, with_actions=with_actions)
        return accounts

    @staticmethod
    def get_perm_accounts_for_permissions(permissions, with_actions=False):
        """ 获取授权规则包含的账号 """
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

    def validate_permission(self, user, asset, account_username):
        """ 校验用户有某个资产下某个账号名的权限 """
        perms, accounts = self.get_perm_accounts_for_user_asset(
            user, asset, with_actions=True, with_perms=True
        )
        perm = perms.first()
        account = accounts.filter(username=account_username).first()
        actions = account.actions if account else []
        expire_at = perm.date_expired if perm else time.time()
        return actions, expire_at
