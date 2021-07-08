import time
from collections import defaultdict

from django.db.models import Q

from common.utils import get_logger
from perms.models import AssetPermission, Action
from perms.hands import Asset, User, UserGroup, SystemUser, Node
from perms.utils.asset.user_permission import get_user_all_asset_perm_ids

logger = get_logger(__file__)


def validate_permission(user, asset, system_user, action_name):

    if not system_user.protocol in asset.protocols_as_dict.keys():
        return False, time.time()

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
    node_ids = Node.objects.filter(key__in=node_keys).values_list('id', flat=True)

    node_ids = set(node_ids)

    asset_perm_ids_from_node = AssetPermission.nodes.through.objects.filter(
        assetpermission_id__in=asset_perm_ids,
        node_id__in=node_ids
    ).values_list('assetpermission_id', flat=True)

    asset_perm_ids = {*asset_perm_ids_from_asset, *asset_perm_ids_from_node}

    asset_perm_ids = AssetPermission.system_users.through.objects.filter(
        assetpermission_id__in=asset_perm_ids,
        systemuser_id=system_user.id
    ).values_list('assetpermission_id', flat=True)

    asset_perm_ids = set(asset_perm_ids)

    asset_perms = AssetPermission.objects.filter(
        id__in=asset_perm_ids
    ).order_by('-date_expired')

    for asset_perm in asset_perms:
        if action_name in Action.value_to_choices(asset_perm.actions):
            return True, asset_perm.date_expired.timestamp()
    return False, time.time()


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


def has_asset_system_permission(user: User, asset: Asset, system_user: SystemUser):
    systemuser_actions_mapper = get_asset_system_user_ids_with_actions_by_user(user, asset)
    actions = systemuser_actions_mapper.get(system_user.id, [])
    if actions:
        return True
    return False


def get_asset_system_user_ids_with_actions_by_group(group: UserGroup, asset: Asset):
    asset_perm_ids = AssetPermission.objects.filter(
        user_groups=group
    ).valid().values_list('id', flat=True).distinct()
    return get_asset_system_user_ids_with_actions(asset_perm_ids, asset)
