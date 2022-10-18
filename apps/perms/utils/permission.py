import time
from collections import defaultdict

from django.db.models import Q

from common.utils import get_logger
from perms.models import AssetPermission, Action
from perms.hands import Asset, User, UserGroup, Node
from perms.utils.user_permission import get_user_all_asset_perm_ids

logger = get_logger(__file__)


class AssetPermissionUtil(object):
    """ 资产授权相关的方法工具 """

    def get_permissions_for_user_asset(self, user, asset):
        """ 获取同时包含用户、资产的授权规则 """
        user_perm_ids = self.get_permissions_for_user(user, flat=True)
        asset_perm_ids = self.get_permissions_for_asset(asset, flat=True)
        perm_ids = set(user_perm_ids) & set(asset_perm_ids)
        perms = AssetPermission.objects.filter(id__in=perm_ids)
        return perms

    def get_permissions_for_user(self, user, with_group=True, flat=False):
        """ 获取用户的授权规则 """
        perm_ids = set()
        # user
        user_perm_ids = AssetPermission.users.through.objects.filter(user_id=user.id) \
            .values_list('assetpermission_id', flat=True).distinct()
        perm_ids.update(user_perm_ids)
        # group
        if with_group:
            groups = user.groups.all()
            group_perm_ids = self.get_permissions_for_user_groups(groups, flat=True)
            perm_ids.update(group_perm_ids)
        if flat:
            return perm_ids
        perms = AssetPermission.objects.filter(id__in=perm_ids)
        return perms

    @staticmethod
    def get_permissions_for_user_groups(user_groups, flat=False):
        """ 获取用户组的授权规则 """
        group_ids = user_groups.values_list('id', flat=True).distinct()
        group_perm_ids = AssetPermission.user_groups.through.objects.filter(usergroup_id__in=group_ids) \
            .values_list('assetpermission_id', flat=True).distinct()
        if flat:
            return group_perm_ids
        perms = AssetPermission.objects.filter(id__in=group_perm_ids)
        return perms

    def get_permissions_for_asset(self, asset, with_node=True, flat=False):
        """ 获取资产的授权规则"""
        perm_ids = set()
        asset_perm_ids = AssetPermission.assets.through.objects.filter(asset_id=asset.id) \
            .values_list('assetpermission_id', flat=True).distinct()
        perm_ids.update(asset_perm_ids)
        if with_node:
            nodes = asset.get_all_nodes(flat=True)
            node_perm_ids = self.get_permissions_for_nodes(nodes, flat=True)
            perm_ids.update(node_perm_ids)
        if flat:
            return perm_ids
        perms = AssetPermission.objects.filter(id__in=perm_ids)
        return perms

    @staticmethod
    def get_permissions_for_nodes(nodes, flat=False):
        """ 获取节点的授权规则 """
        node_ids = nodes.values_list('id', flat=True).distinct()
        node_perm_ids = AssetPermission.nodes.through.objects.filter(node_id__in=node_ids) \
            .values_list('assetpermission_id', flat=True).distinct()
        if flat:
            return node_perm_ids
        perms = AssetPermission.objects.filter(id__in=node_perm_ids)
        return perms


# TODO: 下面的方法放到类中进行实现


def validate_permission(user, asset, account, action='connect'):
    asset_perm_ids = get_user_all_asset_perm_ids(user)

    asset_perm_ids_from_asset = AssetPermission.assets.through.objects.filter(
        assetpermission_id__in=asset_perm_ids,
        asset_id=asset.id
    ).values_list('assetpermission_id', flat=True)

    nodes = asset.get_nodes()
    node_keys = set()
    for node in nodes:
        ancestor_keys = node.get_ancestor_keys(with_self=True)
        node_keys.update(ancestor_keys)
    node_ids = set(Node.objects.filter(key__in=node_keys).values_list('id', flat=True))

    asset_perm_ids_from_node = AssetPermission.nodes.through.objects.filter(
        assetpermission_id__in=asset_perm_ids,
        node_id__in=node_ids
    ).values_list('assetpermission_id', flat=True)

    asset_perm_ids = {*asset_perm_ids_from_asset, *asset_perm_ids_from_node}

    asset_perms = AssetPermission.objects\
        .filter(id__in=asset_perm_ids, accounts__contains=account)\
        .order_by('-date_expired')

    if asset_perms:
        actions = set()
        actions_values = asset_perms.values_list('actions', flat=True)
        for value in actions_values:
            _actions = Action.value_to_choices(value)
            actions.update(_actions)
        asset_perm: AssetPermission = asset_perms.first()
        actions = list(actions)
        expire_at = asset_perm.date_expired.timestamp()
    else:
        actions = []
        expire_at = time.time()

    # TODO: 组件改造API完成后统一通过actions判断has_perm
    has_perm = action in actions
    return has_perm, actions, expire_at


def get_asset_system_user_ids_with_actions(asset_perm_ids, asset: Asset):
    nodes = asset.get_nodes()
    node_keys = set()
    for node in nodes:
        ancestor_keys = node.get_ancestor_keys(with_self=True)
        node_keys.update(ancestor_keys)

    queryset = AssetPermission.objects.filter(id__in=asset_perm_ids)\
        .filter(Q(assets=asset) | Q(nodes__key__in=node_keys))

    asset_protocols = asset.protocols_as_dict.keys()
    values = queryset.filter(
        system_users__protocol__in=asset_protocols
    ).distinct().values_list('system_users', 'actions')
    system_users_actions = defaultdict(int)

    for system_user_id, actions in values:
        if None in (system_user_id, actions):
            continue
        system_users_actions[system_user_id] |= actions
    return system_users_actions


def get_asset_system_user_ids_with_actions_by_user(user: User, asset: Asset):
    asset_perm_ids = get_user_all_asset_perm_ids(user)
    return get_asset_system_user_ids_with_actions(asset_perm_ids, asset)


def has_asset_system_permission(user: User, asset: Asset, account: str):
    systemuser_actions_mapper = get_asset_system_user_ids_with_actions_by_user(user, asset)
    actions = systemuser_actions_mapper.get(account, 0)
    if actions:
        return True
    return False

