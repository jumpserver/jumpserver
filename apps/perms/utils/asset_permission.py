from collections import defaultdict

from django.db.models import Q

from common.utils import get_logger
from ..models import AssetPermission
from ..hands import Asset, User, UserGroup
from perms.models.base import BasePermissionQuerySet

logger = get_logger(__file__)


def get_asset_system_users_id_with_actions(asset_perm_queryset: BasePermissionQuerySet, asset: Asset):
    nodes = asset.get_nodes()
    node_keys = set()
    for node in nodes:
        ancestor_keys = node.get_ancestor_keys(with_self=True)
        node_keys.update(ancestor_keys)

    queryset = asset_perm_queryset.filter(
        Q(assets=asset) |
        Q(nodes__key__in=node_keys)
    )
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


def get_asset_system_users_id_with_actions_by_user(user: User, asset: Asset):
    queryset = AssetPermission.objects.filter(
        Q(users=user) | Q(user_groups__users=user)
    ).valid()
    return get_asset_system_users_id_with_actions(queryset, asset)


def get_asset_system_users_id_with_actions_by_group(group: UserGroup, asset: Asset):
    queryset = AssetPermission.objects.filter(
        user_groups=group
    ).valid()
    return get_asset_system_users_id_with_actions(queryset, asset)
