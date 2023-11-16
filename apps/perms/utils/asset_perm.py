from collections import defaultdict

from accounts.const import AliasAccount
from accounts.models import VirtualAccount
from assets.models import Asset
from common.utils import lazyproperty
from orgs.utils import tmp_to_org, tmp_to_root_org
from .permission import AssetPermissionUtil

__all__ = ['PermAssetDetailUtil']


class PermAssetDetailUtil:
    """ 资产授权账号相关的工具 """

    def __init__(self, user, asset_or_id):
        self.user = user

        if isinstance(asset_or_id, Asset):
            self.asset_id = asset_or_id.id
            self.asset = asset_or_id
        else:
            self.asset_id = asset_or_id

    @lazyproperty
    def asset(self):
        if self.user_asset_perms:
            return self._asset
        raise Asset.DoesNotExist()

    @lazyproperty
    def _asset(self):
        from assets.models import Asset
        with tmp_to_root_org():
            queryset = Asset.objects.filter(id=self.asset_id)
            return queryset.get()

    def validate_permission(self, account_name, protocol):
        with tmp_to_org(self.asset.org):
            protocols = self.get_permed_protocols_for_user(only_name=True)
            if 'all' not in protocols and protocol not in protocols:
                return None
            permed_accounts = self.get_permed_accounts_for_user()
            accounts_mapper = {account.alias: account for account in permed_accounts}
            account = accounts_mapper.get(account_name)
            return account

    @lazyproperty
    def user_asset_perms(self):
        perm_util = AssetPermissionUtil()
        perms = perm_util.get_permissions_for_user_asset(self.user, self.asset_id)
        return perms

    def get_permed_accounts_for_user(self):
        """ 获取授权给用户某个资产的账号 """
        perms = self.user_asset_perms
        permed_accounts = self.get_permed_accounts_from_perms(perms, self.user, self.asset)
        return permed_accounts

    def get_permed_protocols_for_user(self, only_name=False):
        """ 获取授权给用户某个资产的账号 """
        perms = self.user_asset_perms
        names = set()
        for perm in perms:
            names |= set(perm.protocols)
        if only_name:
            return names
        protocols = self.asset.protocols.all()
        if 'all' not in names:
            protocols = protocols.filter(name__in=names)
        return protocols

    @staticmethod
    def parse_alias_action_date_expire(perms, asset):
        alias_action_bit_mapper = defaultdict(int)
        alias_date_expired_mapper = defaultdict(list)

        for perm in perms:
            for alias in perm.accounts:
                alias_action_bit_mapper[alias] |= perm.actions
                alias_date_expired_mapper[alias].append(perm.date_expired)

        # @ALL 账号先处理，后面的每个最多映射一个账号
        all_action_bit = alias_action_bit_mapper.pop(AliasAccount.ALL, None)
        if not all_action_bit:
            return alias_action_bit_mapper, alias_date_expired_mapper

        asset_account_usernames = asset.accounts.all().active().values_list('username', flat=True)
        for username in asset_account_usernames:
            alias_action_bit_mapper[username] |= all_action_bit
            alias_date_expired_mapper[username].extend(
                alias_date_expired_mapper[AliasAccount.ALL]
            )
        return alias_action_bit_mapper, alias_date_expired_mapper

    @classmethod
    def map_alias_to_accounts(cls, alias_action_bit_mapper, alias_date_expired_mapper, asset, user):
        username_accounts_mapper = defaultdict(list)
        cleaned_accounts_expired = defaultdict(list)
        asset_accounts = asset.accounts.all().active()

        # 用户名 -> 账号
        for account in asset_accounts:
            username_accounts_mapper[account.username].append(account)

        cleaned_accounts_action_bit = defaultdict(int)
        for alias, action_bit in alias_action_bit_mapper.items():
            account = None
            _accounts = []
            if alias == AliasAccount.USER and user.username in username_accounts_mapper:
                _accounts = username_accounts_mapper[user.username]
            elif alias in username_accounts_mapper:
                _accounts = username_accounts_mapper[alias]
            elif alias in ['@INPUT', '@ANON', '@USER']:
                account = VirtualAccount.get_special_account(alias, user, asset, from_permed=True)
            elif alias.startswith('@'):
                continue

            if account:
                _accounts += [account]

            for account in _accounts:
                cleaned_accounts_action_bit[account] |= action_bit
                cleaned_accounts_expired[account].extend(alias_date_expired_mapper[alias])
        return cleaned_accounts_action_bit, cleaned_accounts_expired

    @classmethod
    def get_permed_accounts_from_perms(cls, perms, user, asset):
        # alias: is a collection of account usernames and special accounts [@ALL, @INPUT, @USER, @ANON]
        alias_action_bit_mapper, alias_date_expired_mapper = cls.parse_alias_action_date_expire(perms, asset)
        cleaned_accounts_action_bit, cleaned_accounts_expired = cls.map_alias_to_accounts(
            alias_action_bit_mapper, alias_date_expired_mapper, asset, user
        )
        accounts = []
        for account, action_bit in cleaned_accounts_action_bit.items():
            account.actions = action_bit
            account.date_expired = max(cleaned_accounts_expired[account])
            accounts.append(account)
        return accounts
