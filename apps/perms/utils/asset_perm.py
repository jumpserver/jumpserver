from collections import defaultdict
from dataclasses import dataclass

from accounts.const import AliasAccount
from accounts.models import Account, VirtualAccount
from assets.models import Asset, MyAsset, Node, Protocol
from common.utils import lazyproperty, get_logger
from orgs.utils import tmp_to_org, tmp_to_root_org
from perms.const import ActionChoices
from perms.models import AssetPermission
from .permission import AssetPermissionUtil

logger = get_logger(__name__)

__all__ = ['PermAssetAccountsBatchUtil', 'PermAssetDetailUtil']


@dataclass(frozen=True)
class PermAssetAccountsBatchContext:
    """Input data shared while resolving permitted accounts for assets."""

    permissions_by_id: dict
    asset_protocols: dict
    asset_usernames: dict
    required_protocols: set
    action_required: int


class PermAssetAccountsBatchUtil:
    """Resolve a user's permitted real accounts for multiple assets in bulk."""

    def __init__(self, user):
        """Initialize the resolver for a user."""
        self.user = user

    @staticmethod
    def permission_matches_protocol(permission, protocols):
        permitted = set(permission.protocols or [])
        return 'all' in permitted or bool(permitted.intersection(protocols))

    @staticmethod
    def get_node_ancestor_keys(key):
        parts = key.split(':')
        return {
            ':'.join(parts[:index])
            for index in range(1, len(parts) + 1)
        }

    def get_asset_permission_ids(self, asset_ids, permission_ids):
        asset_permission_ids = defaultdict(set)
        direct_relations = AssetPermission.assets.through.objects.filter(
            asset_id__in=asset_ids,
            assetpermission_id__in=permission_ids,
        ).values_list('asset_id', 'assetpermission_id')
        for asset_id, permission_id in direct_relations:
            asset_permission_ids[asset_id].add(permission_id)

        asset_node_relations = self.get_asset_node_relations(asset_ids)

        ancestor_assets = defaultdict(set)
        for asset_id, node_key in asset_node_relations:
            for ancestor_key in self.get_node_ancestor_keys(node_key):
                ancestor_assets[ancestor_key].add(asset_id)

        ancestor_keys = set(ancestor_assets)
        if not ancestor_keys:
            return asset_permission_ids
        permission_node_relations = (
            AssetPermission.nodes.through.objects.filter(
                assetpermission_id__in=permission_ids,
                node__key__in=ancestor_keys,
            ).values_list('assetpermission_id', 'node__key')
        )
        for permission_id, node_key in permission_node_relations:
            for asset_id in ancestor_assets.get(node_key, set()):
                asset_permission_ids[asset_id].add(permission_id)
        return asset_permission_ids

    @staticmethod
    def get_asset_node_relations(asset_ids):
        asset_node_relations = list(
            Asset.nodes.through.objects.filter(
                asset_id__in=asset_ids,
            ).values_list('asset_id', 'node__key')
        )
        assets_with_nodes = {
            asset_id for asset_id, _key in asset_node_relations
        }
        assets_without_nodes = set(asset_ids) - assets_with_nodes
        if assets_without_nodes:
            root_key = Node.org_root().key
            if root_key:
                asset_node_relations.extend(
                    (asset_id, root_key) for asset_id in assets_without_nodes
                )
        return asset_node_relations

    @staticmethod
    def get_asset_protocols(asset_ids):
        asset_protocols = defaultdict(set)
        relations = Protocol.objects.filter(
            asset_id__in=asset_ids,
        ).values_list('asset_id', 'name')
        for asset_id, protocol in relations:
            asset_protocols[asset_id].add(protocol)
        return asset_protocols

    @staticmethod
    def get_asset_account_usernames(asset_ids):
        source_asset_ids = set(asset_ids)
        source_targets = defaultdict(set)
        for asset_id in asset_ids:
            source_targets[asset_id].add(asset_id)

        directory_relations = (
            Asset.directory_services.through.objects.filter(
                asset_id__in=asset_ids,
            ).values_list('asset_id', 'directoryservice_id')
        )
        for asset_id, directory_service_id in directory_relations:
            source_asset_ids.add(directory_service_id)
            source_targets[directory_service_id].add(asset_id)

        asset_usernames = defaultdict(list)
        accounts = Account.objects.filter(
            asset_id__in=source_asset_ids,
            is_active=True,
        ).values_list('asset_id', 'username')
        for source_asset_id, username in accounts:
            for target_asset_id in source_targets[source_asset_id]:
                asset_usernames[target_asset_id].append(username)
        return asset_usernames

    @staticmethod
    def get_alias_actions(permissions):
        alias_actions = defaultdict(int)
        for permission in permissions:
            for alias in permission.accounts:
                alias_actions[alias] |= permission.actions
        return alias_actions

    @staticmethod
    def expand_all_alias(alias_actions, account_usernames):
        all_actions = alias_actions.pop(AliasAccount.ALL, 0)
        if not all_actions:
            return
        for username in account_usernames:
            alias_actions[username] |= all_actions

    @staticmethod
    def apply_exclusions(alias_actions):
        exclusions = {
            alias: actions
            for alias, actions in alias_actions.items()
            if alias.startswith('!')
        }
        for alias, actions in exclusions.items():
            alias_actions.pop(alias, None)
            alias_actions[alias.lstrip('!')] &= ~actions

    def resolve_alias_actions(self, alias_actions, account_usernames):
        resolved_actions = defaultdict(int)
        for alias, actions in alias_actions.items():
            if actions <= 0:
                continue
            if alias == AliasAccount.USER:
                username = self.user.username
            elif alias.startswith('@'):
                continue
            else:
                username = alias
            if username in account_usernames:
                resolved_actions[username] |= actions
        return resolved_actions

    def get_asset_permitted_usernames(
        self, asset_id, permission_ids, context,
    ):
        actual_protocols = context.asset_protocols.get(asset_id, set())
        protocols = (
            actual_protocols.intersection(context.required_protocols)
            if context.required_protocols else actual_protocols
        )
        if not protocols:
            return []

        permissions = (
            context.permissions_by_id[permission_id]
            for permission_id in permission_ids
            if self.permission_matches_protocol(
                context.permissions_by_id[permission_id], protocols,
            )
        )
        account_usernames = context.asset_usernames.get(asset_id, [])
        account_username_set = set(account_usernames)
        alias_actions = self.get_alias_actions(permissions)
        self.expand_all_alias(alias_actions, account_username_set)
        self.apply_exclusions(alias_actions)
        resolved_actions = self.resolve_alias_actions(
            alias_actions, account_username_set,
        )

        return [
            username for username in account_usernames
            if not username.startswith(('jms_', 'js_'))
            and ActionChoices.contains(
                resolved_actions.get(username, 0), context.action_required,
            )
        ]

    def get_permitted_account_usernames(
        self, assets, action_required, protocols_required=None,
    ):
        asset_ids = [asset.id for asset in assets]
        if not asset_ids:
            return []

        permissions = list(
            AssetPermissionUtil().get_permissions_for_user(self.user).only(
                'id', 'accounts', 'protocols', 'actions',
            )
        )
        permissions_by_id = {
            permission.id: permission for permission in permissions
        }
        permission_ids = list(permissions_by_id)
        if not permission_ids:
            return []

        asset_permission_ids = self.get_asset_permission_ids(
            asset_ids, permission_ids,
        )
        asset_ids = [
            asset_id for asset_id in asset_ids
            if asset_permission_ids.get(asset_id)
        ]
        if not asset_ids:
            return []

        context = PermAssetAccountsBatchContext(
            permissions_by_id=permissions_by_id,
            asset_protocols=self.get_asset_protocols(asset_ids),
            asset_usernames=self.get_asset_account_usernames(asset_ids),
            required_protocols=set(protocols_required or []),
            action_required=action_required,
        )

        usernames = []
        for asset_id in asset_ids:
            usernames.extend(self.get_asset_permitted_usernames(
                asset_id,
                asset_permission_ids[asset_id],
                context,
            ))
        return usernames


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
            asset = self._asset
            MyAsset.set_asset_custom_value([asset], self.user)
            return asset
        raise Asset.DoesNotExist()

    @lazyproperty
    def _asset(self):
        from assets.models import Asset
        with tmp_to_root_org():
            queryset = Asset.objects.filter(id=self.asset_id)
            return queryset.get()

    def validate_permission(self, account_alias, protocol):
        with tmp_to_org(self.asset.org):
            protocols = self.get_permed_protocols_for_user(only_name=True)
            if 'all' not in protocols and protocol not in protocols:
                return None
            permed_accounts = self.get_permed_accounts_for_user()
            accounts_mapper = {account.alias: account for account in permed_accounts}
            account = accounts_mapper.get(account_alias)
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
        if all_action_bit:
            asset_account_usernames = asset.all_valid_accounts.values_list('username', flat=True)
            for username in asset_account_usernames:
                alias_action_bit_mapper[username] |= all_action_bit
                alias_date_expired_mapper[username].extend(
                    alias_date_expired_mapper[AliasAccount.ALL]
                )

        # 排除某些账号的权限
        exclude_alias_action_mapper = {
            alias: action 
            for alias, action in alias_action_bit_mapper.items() 
            if alias.startswith('!')
        }

        for alias, action in exclude_alias_action_mapper.items():
            alias_action_bit_mapper.pop(alias, None)
            account = alias.lstrip('!')
            alias_action_bit_mapper[account] -= action
            
        # 排除掉没有 action 的账号
        alias_action_bit_mapper = {
            alias: action_bit
            for alias, action_bit in alias_action_bit_mapper.items()
            if action_bit and action_bit > 0
        }

        return alias_action_bit_mapper, alias_date_expired_mapper

    @classmethod
    def map_alias_to_accounts(cls, alias_action_bit_mapper, alias_date_expired_mapper, asset, user):
        username_accounts_mapper = defaultdict(list)
        cleaned_accounts_expired = defaultdict(list)
        asset_accounts = asset.all_valid_accounts.all()

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
        # 展开 alias 到具体的账号
        cleaned_accounts_action_bit, cleaned_accounts_expired = cls.map_alias_to_accounts(
            alias_action_bit_mapper, alias_date_expired_mapper, asset, user
        )
        accounts = []
        virtual_accounts = []
        for account, action_bit in cleaned_accounts_action_bit.items():
            account.actions = action_bit
            all_date_expired = cleaned_accounts_expired[account]
            if not all_date_expired:
                logger.warning(f"Account {account.username} has no date expired")
                continue
            account.date_expired = max(all_date_expired)

            if account.username.startswith('@'):
                virtual_accounts.append(account)
            else:
                accounts.append(account)
        accounts.sort(key=lambda x: x.username)
        virtual_accounts.sort(key=lambda x: x.username)
        return accounts + virtual_accounts

    def check_perm_protocols(self, protocols):
        """
        检查用户是否有某些协议权限
        :param protocols: set
        """
        perms_protocols = self.get_permed_protocols_for_user(only_name=True)
        if "all" in perms_protocols:
            return True
        return protocols.intersection(perms_protocols)

    def check_perm_actions(self, account_name, actions):
        """
        检查用户是否有某个账号的某个资产操作权限
        :param account_name: str
        :param actions: list
        """
        perms = self.user_asset_perms
        action_bit_mapper, __ = self.parse_alias_action_date_expire(perms, self.asset)
        return ActionChoices.contains_all(action_bit_mapper.get(account_name, 0), actions)
