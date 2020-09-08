from collections import defaultdict

from django.db.models import Q

from common.utils import get_logger
from ..models import AssetPermission
from ..hands import Asset, User
from users.models import UserGroup
from perms.models.base import BasePermissionQuerySet

logger = get_logger(__file__)


def get_user_permissions(user, include_group=True):
    if include_group:
        groups = user.groups.all()
        arg = Q(users=user) | Q(user_groups__in=groups)
    else:
        arg = Q(users=user)
    return AssetPermission.get_queryset_with_prefetch().filter(arg)


def get_user_group_permissions(user_group):
    return AssetPermission.get_queryset_with_prefetch().filter(
        user_groups=user_group
    )


def get_asset_permissions(asset, include_node=True):
    if include_node:
        nodes = asset.get_all_nodes(flat=True)
        arg = Q(assets=asset) | Q(nodes__in=nodes)
    else:
        arg = Q(assets=asset)
    return AssetPermission.objects.valid().filter(arg)


def get_node_permissions(node):
    return AssetPermission.objects.valid().filter(nodes=node)


def get_system_user_permissions(system_user):
    return AssetPermission.objects.valid().filter(
        system_users=system_user
    )


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
    )
    return get_asset_system_users_id_with_actions(queryset, asset)


def get_asset_system_users_id_with_actions_by_group(group: UserGroup, asset: Asset):
    queryset = AssetPermission.objects.filter(
        user_groups=group
    )
    return get_asset_system_users_id_with_actions(queryset, asset)
