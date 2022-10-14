from collections import defaultdict
from assets.models import Account
from perms.models import AssetPermission


class PermAccountUtil(object):
    """ 授权账号查询工具 """

    # Accounts

    def get_user_perm_asset_accounts(self, user, asset, with_actions=False):
        """ 获取授权给用户某个资产的账号 """
        perms = self.get_user_asset_permissions(user, asset)
        accounts = self.get_permissions_accounts(perms, with_actions=with_actions)
        return accounts

    def get_user_perm_accounts(self, user, with_actions=False):
        """ 获取授权给用户的所有账号 """
        perms = self.get_user_permissions(user)
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

    # Permissions

    def get_user_asset_permissions(self, user, asset):
        """ 获取同时包含用户、资产的授权规则 """
        user_perm_ids = self.get_user_permissions(user, flat=True)
        asset_perm_ids = self.get_asset_permissions(asset, flat=True)
        perm_ids = set(user_perm_ids) & set(asset_perm_ids)
        perms = AssetPermission.objects.filter(id__in=perm_ids)
        return perms

    def get_user_permissions(self, user, with_group=True, flat=False):
        """ 获取用户的授权规则 """
        perm_ids = set()
        # user
        user_perm_ids = AssetPermission.users.through.objects.filter(user_id=user.id)\
            .values_list('assetpermission_id', flat=True).distinct()
        perm_ids.update(user_perm_ids)
        # group
        if with_group:
            groups = user.groups.all()
            group_perm_ids = self.get_user_groups_permissions(groups, flat=True)
            perm_ids.update(group_perm_ids)
        if flat:
            return perm_ids
        perms = AssetPermission.objects.filter(id__in=perm_ids)
        return perms

    @staticmethod
    def get_user_groups_permissions(user_groups, flat=False):
        """ 获取用户组的授权规则 """
        group_ids = user_groups.values_list('id', flat=True).distinct()
        perm_ids = AssetPermission.user_groups.through.objects.filter(usergroup_id__in=group_ids) \
            .values_list('assetpermission_id', flat=True).distinct()
        if flat:
            return perm_ids
        perms = AssetPermission.objects.filter(id__in=perm_ids)
        return perms

    def get_asset_permissions(self, asset, flat=False):
        """ 获取资产的授权规则"""
        return AssetPermission.objects.all()

    def get_node_permissions(self):
        """ 获取节点的授权规则 """
        pass

