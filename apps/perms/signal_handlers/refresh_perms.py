# -*- coding: utf-8 -*-
#
from django.db.models.signals import m2m_changed, pre_delete, pre_save, post_save
from django.dispatch import receiver

from assets.models import Asset
from common.const.signals import POST_ADD, POST_REMOVE, POST_CLEAR
from common.exceptions import M2MReverseNotAllowed
from common.utils import get_logger, get_object_or_none
from perms.models import AssetPermission
from perms.utils import UserPermTreeExpireUtil
from users.models import User, UserGroup

logger = get_logger(__file__)


@receiver(pre_delete, sender=UserGroup)
def on_user_group_delete(sender, instance: UserGroup, using, **kwargs):
    exists = AssetPermission.user_groups.through.objects.filter(usergroup_id=instance.id).exists()
    if not exists:
        return
    UserPermTreeExpireUtil().expire_perm_tree_for_user_group(instance)


@receiver(m2m_changed, sender=User.groups.through)
def on_user_groups_change(sender, instance, action, reverse, pk_set, **kwargs):
    if not action.startswith('post'):
        return
    if reverse:
        group_ids = [instance.id]
        user_ids = pk_set
        org_id = instance.org_id
    else:
        group_ids = pk_set
        user_ids = [instance.id]
        group = UserGroup.objects.get(id=list(group_ids)[0])
        org_id = group.org_id

    has_group_perm = AssetPermission.user_groups.through.objects \
        .filter(usergroup_id__in=group_ids).exists()
    if not has_group_perm:
        return

    UserPermTreeExpireUtil().expire_perm_tree_for_users_orgs(user_ids, [org_id])


@receiver([pre_delete], sender=AssetPermission)
def on_asset_perm_pre_delete(sender, instance, **kwargs):
    UserPermTreeExpireUtil().expire_perm_tree_for_perms([instance.id])


@receiver([pre_save], sender=AssetPermission)
def on_asset_perm_pre_save(sender, instance, **kwargs):
    old = get_object_or_none(AssetPermission, pk=instance.id)
    if not old:
        return
    if old.is_valid == instance.is_valid:
        return
    UserPermTreeExpireUtil().expire_perm_tree_for_perms([instance.id])


@receiver([post_save], sender=AssetPermission)
def on_asset_perm_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    UserPermTreeExpireUtil().expire_perm_tree_for_perms([instance.id])


def need_rebuild_mapping_node(action):
    return action in (POST_REMOVE, POST_ADD, POST_CLEAR)


@receiver(m2m_changed, sender=AssetPermission.nodes.through)
def on_permission_nodes_changed(sender, instance, action, reverse, **kwargs):
    if not need_rebuild_mapping_node(action):
        return
    if reverse:
        raise M2MReverseNotAllowed
    UserPermTreeExpireUtil().expire_perm_tree_for_perms([instance.id])


@receiver(m2m_changed, sender=AssetPermission.assets.through)
def on_permission_assets_changed(sender, instance, action, reverse, pk_set, model, **kwargs):
    if not need_rebuild_mapping_node(action):
        return
    if reverse:
        raise M2MReverseNotAllowed
    UserPermTreeExpireUtil().expire_perm_tree_for_perms([instance.id])


@receiver(m2m_changed, sender=AssetPermission.users.through)
def on_asset_permission_users_changed(sender, action, reverse, instance, pk_set, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed
    if not need_rebuild_mapping_node(action):
        return
    user_ids = pk_set
    UserPermTreeExpireUtil().expire_perm_tree_for_users_orgs(user_ids, [instance.org.id])


@receiver(m2m_changed, sender=AssetPermission.user_groups.through)
def on_asset_permission_user_groups_changed(sender, instance, action, pk_set, reverse, **kwargs):
    if not need_rebuild_mapping_node(action):
        return
    if reverse:
        raise M2MReverseNotAllowed

    group_ids = pk_set
    UserPermTreeExpireUtil().expire_perm_tree_for_user_groups_orgs(group_ids, [instance.org.id])


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_node_asset_change(action, instance, reverse, pk_set, **kwargs):
    if not need_rebuild_mapping_node(action):
        return
    print("Asset node changed: ", action)
    if reverse:
        asset_ids = pk_set
        node_ids = [instance.id]
    else:
        asset_ids = [instance.id]
        node_ids = pk_set

    UserPermTreeExpireUtil().expire_perm_tree_for_nodes_assets(node_ids, asset_ids)
