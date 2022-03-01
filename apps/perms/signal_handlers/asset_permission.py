# -*- coding: utf-8 -*-
#
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from users.models import User
from assets.models import SystemUser
from common.utils import get_logger
from common.decorator import on_transaction_commit
from common.exceptions import M2MReverseNotAllowed
from common.const.signals import POST_ADD
from perms.models import AssetPermission


logger = get_logger(__file__)


@receiver(m2m_changed, sender=User.groups.through)
@on_transaction_commit
def on_user_groups_change(sender, instance, action, reverse, pk_set, **kwargs):
    """
    UserGroup 增加 User 时，增加的 User 需要与 UserGroup 关联的动态系统用户相关联
    """
    user: User

    if action != POST_ADD:
        return

    if not reverse:
        # 一个用户添加了多个用户组
        user_ids = [instance.id]
        system_users = SystemUser.objects.filter(groups__id__in=pk_set).distinct()
    else:
        # 一个用户组添加了多个用户
        user_ids = pk_set
        system_users = SystemUser.objects.filter(groups__id=instance.pk).distinct()

    for system_user in system_users:
        system_user.users.add(*user_ids)


@receiver(m2m_changed, sender=AssetPermission.nodes.through)
@on_transaction_commit
def on_permission_nodes_changed(instance, action, reverse, pk_set, model, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed
    if action != POST_ADD:
        return

    logger.debug("Asset permission nodes change signal received")
    nodes = model.objects.filter(pk__in=pk_set)
    system_users = instance.system_users.all()

    # TODO 待优化
    for system_user in system_users:
        system_user.nodes.add(*nodes)


@receiver(m2m_changed, sender=AssetPermission.assets.through)
@on_transaction_commit
def on_permission_assets_changed(instance, action, reverse, pk_set, model, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed
    if action != POST_ADD:
        return

    logger.debug("Asset permission assets change signal received")
    assets = model.objects.filter(pk__in=pk_set)

    # TODO 待优化
    system_users = instance.system_users.all()
    for system_user in system_users:
        system_user: SystemUser
        system_user.add_related_assets(assets)


@receiver(m2m_changed, sender=AssetPermission.system_users.through)
@on_transaction_commit
def on_asset_permission_system_users_changed(instance, action, reverse, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed
    if action != POST_ADD:
        return

    logger.debug("Asset permission system_users change signal received")
    system_users = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
    assets = instance.assets.all().values_list('id', flat=True)
    nodes = instance.nodes.all().values_list('id', flat=True)

    for system_user in system_users:
        system_user.nodes.add(*tuple(nodes))
        system_user.add_related_assets(assets)

        # 动态系统用户，需要关联用户和用户组了
        if system_user.username_same_with_user:
            users = instance.users.all().values_list('id', flat=True)
            groups = instance.user_groups.all().values_list('id', flat=True)
            system_user.groups.add(*tuple(groups))
            system_user.users.add(*tuple(users))


@receiver(m2m_changed, sender=AssetPermission.users.through)
@on_transaction_commit
def on_asset_permission_users_changed(instance, action, reverse, pk_set, model, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed
    if action != POST_ADD:
        return

    logger.debug("Asset permission users change signal received")
    users = model.objects.filter(pk__in=pk_set)
    system_users = instance.system_users.all()

    # TODO 待优化
    for system_user in system_users:
        if system_user.username_same_with_user:
            system_user.users.add(*tuple(users))


@receiver(m2m_changed, sender=AssetPermission.user_groups.through)
@on_transaction_commit
def on_asset_permission_user_groups_changed(instance, action, pk_set, model, reverse, **kwargs):
    if reverse:
        raise M2MReverseNotAllowed
    if action != POST_ADD:
        return

    logger.debug("Asset permission user groups change signal received")
    groups = model.objects.filter(pk__in=pk_set)
    system_users = instance.system_users.all()

    # TODO 待优化
    for system_user in system_users:
        if system_user.username_same_with_user:
            system_user.groups.add(*tuple(groups))





