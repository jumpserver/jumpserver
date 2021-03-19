# -*- coding: utf-8 -*-
#
from django.db.models.signals import m2m_changed, pre_delete, pre_save, post_save
from django.dispatch import receiver

from users.models import User, UserGroup
from assets.models import Asset
from orgs.utils import current_org, tmp_to_org
from common.utils import get_logger
from common.exceptions import M2MReverseNotAllowed
from common.const.signals import POST_ADD, POST_REMOVE, POST_CLEAR
from perms.models import AssetPermission
from perms.utils.asset.user_permission import UserGrantedTreeRefreshController


logger = get_logger(__file__)


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

    exists = AssetPermission.user_groups.through.objects.filter(usergroup_id__in=group_ids).exists()
    if not exists:
        return

    org_ids = [org_id]
    UserGrantedTreeRefreshController.add_need_refresh_orgs_for_users(org_ids, user_ids)


@receiver([pre_delete], sender=AssetPermission)
def on_asset_perm_pre_delete(sender, instance, **kwargs):
    # 授权删除之前，查出所有相关用户
    with tmp_to_org(instance.org):
        UserGrantedTreeRefreshController.add_need_refresh_by_asset_perm_ids([instance.id])


@receiver([pre_save], sender=AssetPermission)
def on_asset_perm_pre_save(sender, instance, **kwargs):
    try:
        old = AssetPermission.objects.get(id=instance.id)

        if old.is_valid != instance.is_valid:
            with tmp_to_org(instance.org):
                UserGrantedTreeRefreshController.add_need_refresh_by_asset_perm_ids([instance.id])
    except AssetPermission.DoesNotExist:
        pass


@receiver([post_save], sender=AssetPermission)
def on_asset_perm_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    with tmp_to_org(instance.org):
        UserGrantedTreeRefreshController.add_need_refresh_by_asset_perm_ids([instance.id])


def need_rebuild_mapping_node(action):
    return action in (POST_REMOVE, POST_ADD, POST_CLEAR)


@receiver(m2m_changed, sender=AssetPermission.nodes.through)
def on_permission_nodes_changed(sender, instance, action, reverse, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed

    if not need_rebuild_mapping_node(action):
        return

    with tmp_to_org(instance.org):
        UserGrantedTreeRefreshController.add_need_refresh_by_asset_perm_ids([instance.id])


@receiver(m2m_changed, sender=AssetPermission.assets.through)
def on_permission_assets_changed(sender, instance, action, reverse, pk_set, model, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed

    if not need_rebuild_mapping_node(action):
        return
    with tmp_to_org(instance.org):
        UserGrantedTreeRefreshController.add_need_refresh_by_asset_perm_ids([instance.id])


@receiver(m2m_changed, sender=AssetPermission.users.through)
def on_asset_permission_users_changed(sender, action, reverse, instance, pk_set, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed

    if not need_rebuild_mapping_node(action):
        return

    with tmp_to_org(instance.org):
        UserGrantedTreeRefreshController.add_need_refresh_orgs_for_users(
            [current_org.id], pk_set
        )


@receiver(m2m_changed, sender=AssetPermission.user_groups.through)
def on_asset_permission_user_groups_changed(sender, instance, action, pk_set, reverse, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed

    if not need_rebuild_mapping_node(action):
        return

    user_ids = User.groups.through.objects.filter(usergroup_id__in=pk_set) \
        .values_list('user_id', flat=True) \
        .distinct()
    with tmp_to_org(instance.org):
        UserGrantedTreeRefreshController.add_need_refresh_orgs_for_users(
            [current_org.id], user_ids
        )


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_node_asset_change(action, instance, reverse, pk_set, **kwargs):
    if not need_rebuild_mapping_node(action):
        return

    if reverse:
        asset_pk_set = pk_set
        node_pk_set = [instance.id]
    else:
        asset_pk_set = [instance.id]
        node_pk_set = pk_set

    with tmp_to_org(instance.org):
        UserGrantedTreeRefreshController.add_need_refresh_on_nodes_assets_relate_change(node_pk_set, asset_pk_set)
