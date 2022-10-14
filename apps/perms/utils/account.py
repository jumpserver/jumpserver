from collections import defaultdict
from assets.models import Account
from perms.models import AssetPermission


class PermAccountUtil(object):
    """ 授权账号查询工具 """

    # Accounts

    def get_user_perm_asset_accounts(self, user, asset, with_actions=False):
        """ 获取授权给用户某个资产的账号 """
        aid_actions_map = defaultdict(int)
        perms = self.get_user_asset_permissions(user, asset)
        for perm in perms:
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

    def get_user_perm_accounts(self, user):
        """ 获取授权给用户的所有账号 """
        pass

    # Permissions

    def get_user_asset_permissions(self, user, asset):
        """ 获取同时包含用户、资产的授权规则 """
        return AssetPermission.objects.all()

    def get_user_permissions(self):
        """ 获取用户的授权规则 """
        pass

    def get_asset_permissions(self):
        """ 获取资产的授权规则"""
        pass

    def get_node_permissions(self):
        """ 获取节点的授权规则 """
        pass

    def get_user_group_permissions(self):
        """ 获取用户组的授权规则 """
        pass
