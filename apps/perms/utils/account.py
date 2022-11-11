import time
from collections import defaultdict

from assets.models import Account
from .permission import AssetPermissionUtil

__all__ = ['PermAccountUtil']


class PermAccountUtil(AssetPermissionUtil):
    """ 资产授权账号相关的工具 """
    @staticmethod
    def get_permed_accounts_from_perms(perms, user, asset):
        alias_action_bit_mapper = defaultdict(int)
        alias_expired_mapper = defaultdict(list)

        for perm in perms:
            for alias in perm.accounts:
                alias_action_bit_mapper[alias] |= perm.actions
                alias_expired_mapper[alias].append(perm.date_expired)

        asset_accounts = asset.accounts.all()
        username_account_mapper = {account.username: account for account in asset_accounts}
        cleaned_accounts_action_bit = defaultdict(int)
        cleaned_accounts_expired = defaultdict(list)

        # @ALL 账号先处理，后面的每个最多映射一个账号
        all_action_bit = alias_action_bit_mapper.pop('@ALL', None)
        if all_action_bit:
            for account in asset_accounts:
                cleaned_accounts_action_bit[account] |= all_action_bit
                cleaned_accounts_expired[account].extend(alias_expired_mapper['@ALL'])

        for alias, action_bit in alias_action_bit_mapper.items():
            if alias == '@USER':
                if user.username in username_account_mapper:
                    account = username_account_mapper[user.username]
                else:
                    account = Account.get_user_account(user.username)
            elif alias == '@INPUT':
                account = Account.get_manual_account()
            elif alias in username_account_mapper:
                account = username_account_mapper[alias]
            else:
                account = None

            if account:
                cleaned_accounts_action_bit[account] |= action_bit
                cleaned_accounts_expired[account].extend(alias_expired_mapper[alias])

        accounts = []
        for account, action_bit in cleaned_accounts_action_bit.items():
            account.actions = action_bit
            account.date_expired = max(cleaned_accounts_expired[account])
            accounts.append(account)
        return accounts

    def get_permed_accounts_for_user(self, user, asset):
        """ 获取授权给用户某个资产的账号 """
        perms = self.get_permissions_for_user_asset(user, asset)
        permed_accounts = self.get_permed_accounts_from_perms(perms, user, asset)
        return permed_accounts

    @staticmethod
    def get_accounts_for_permission(perm, with_actions=False):
        """ 获取授权规则包含的账号 """
        aid_actions_map = defaultdict(int)
        # 这里不行，速度太慢, 别情有很多查询
        account_ids = perm.get_all_accounts(flat=True)
        actions = perm.actions
        for aid in account_ids:
            aid_actions_map[str(aid)] |= actions
        account_ids = list(aid_actions_map.keys())
        accounts = Account.objects.filter(id__in=account_ids)
        return accounts

    def validate_permission(self, user, asset, account_username):
        """ 校验用户有某个资产下某个账号名的权限 """
        permed_accounts = self.get_permed_accounts_for_user(user, asset)
        accounts_mapper = {account.username: account for account in permed_accounts}

        account = accounts_mapper.get(account_username)
        if not account:
            return False, None
        else:
            return account.actions, account.date_expired
