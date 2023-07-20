from collections import defaultdict

from accounts.const import AliasAccount
from accounts.models import Account
from orgs.utils import tmp_to_org
from .permission import AssetPermissionUtil

__all__ = ['PermAccountUtil']


class PermAccountUtil(AssetPermissionUtil):
    """ 资产授权账号相关的工具 """

    def validate_permission(self, user, asset, account_name):
        """ 校验用户有某个资产下某个账号名的权限
        :param user: User
        :param asset: Asset
        :param account_name: 可能是 @USER @INPUT 字符串
        """
        with tmp_to_org(asset.org):
            permed_accounts = self.get_permed_accounts_for_user(user, asset)
            accounts_mapper = {account.alias: account for account in permed_accounts}
            account = accounts_mapper.get(account_name)
            return account

    def get_permed_accounts_for_user(self, user, asset):
        """ 获取授权给用户某个资产的账号 """
        perms = self.get_permissions_for_user_asset(user, asset)
        permed_accounts = self.get_permed_accounts_from_perms(perms, user, asset)
        return permed_accounts

    @staticmethod
    def get_permed_accounts_from_perms(perms, user, asset):
        # alias: is a collection of account usernames and special accounts [@ALL, @INPUT, @USER, @ANON]
        alias_action_bit_mapper = defaultdict(int)
        alias_date_expired_mapper = defaultdict(list)

        for perm in perms:
            for alias in perm.accounts:
                alias_action_bit_mapper[alias] |= perm.actions
                alias_date_expired_mapper[alias].append(perm.date_expired)

        asset_accounts = asset.accounts.all().active()
        # username_accounts_mapper = {account.username: account for account in asset_accounts}
        username_accounts_mapper = defaultdict(list)
        for account in asset_accounts:
            username_accounts_mapper[account.username].append(account)

        cleaned_accounts_action_bit = defaultdict(int)
        cleaned_accounts_expired = defaultdict(list)

        # @ALL 账号先处理，后面的每个最多映射一个账号
        all_action_bit = alias_action_bit_mapper.pop(AliasAccount.ALL, None)
        if all_action_bit:
            for account in asset_accounts:
                cleaned_accounts_action_bit[account] |= all_action_bit
                cleaned_accounts_expired[account].extend(
                    alias_date_expired_mapper[AliasAccount.ALL]
                )

        for alias, action_bit in alias_action_bit_mapper.items():
            account = None
            _accounts = []
            if alias == AliasAccount.USER:
                if user.username in username_accounts_mapper:
                    _accounts = username_accounts_mapper[user.username]
                else:
                    account = Account.get_user_account()
            elif alias == AliasAccount.INPUT:
                account = Account.get_manual_account()
            elif alias == AliasAccount.ANON:
                account = Account.get_anonymous_account()
            elif alias in username_accounts_mapper:
                _accounts = username_accounts_mapper[alias]
            elif alias.startswith('@'):
                continue

            if account:
                _accounts += [account]

            for account in _accounts:
                cleaned_accounts_action_bit[account] |= action_bit
                cleaned_accounts_expired[account].extend(alias_date_expired_mapper[alias])

        accounts = []
        for account, action_bit in cleaned_accounts_action_bit.items():
            account.actions = action_bit
            account.date_expired = max(cleaned_accounts_expired[account])
            accounts.append(account)
        return accounts
