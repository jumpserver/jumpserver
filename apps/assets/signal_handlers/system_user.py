# -*- coding: utf-8 -*-
#
from django.db.models.signals import (
    post_save, m2m_changed
)
from django.dispatch import receiver

from common.exceptions import M2MReverseNotAllowed
from common.const.signals import POST_ADD
from common.utils import get_logger
from common.decorator import on_transaction_commit
from assets.models import Asset, SystemUser, Node
from users.models import User
from assets.tasks import (
    push_system_user_to_assets_manual,
    push_system_user_to_assets,
    add_nodes_assets_to_system_users
)

logger = get_logger(__file__)


@receiver(m2m_changed, sender=SystemUser.assets.through)
@on_transaction_commit
def on_system_user_assets_change(instance, action, model, pk_set, **kwargs):
    """
    当系统用户和资产关系发生变化时，应该重新推送系统用户到新添加的资产中
    """
    logger.debug("System user assets change signal recv: {}".format(instance))

    if not instance:
        logger.debug('No system user found')
        return

    if action != POST_ADD:
        return

    if model == Asset:
        system_user_ids = [instance.id]
        asset_ids = pk_set
    else:
        system_user_ids = pk_set
        asset_ids = [instance.id]
    # todo: Auto create account if need
    SystemUser.create_accounts_with_assets(asset_ids, system_user_ids)


@receiver(m2m_changed, sender=SystemUser.users.through)
@on_transaction_commit
def on_system_user_users_change(sender, instance: SystemUser, action, model, pk_set, reverse, **kwargs):
    """
    当系统用户和用户关系发生变化时，应该重新推送系统用户资产中
    """
    if action != POST_ADD:
        return

    if reverse:
        raise M2MReverseNotAllowed

    if not instance.username_same_with_user:
        return

    logger.debug("System user users change signal recv: {}".format(instance))
    usernames = model.objects.filter(pk__in=pk_set).values_list('username', flat=True)

    for username in usernames:
        push_system_user_to_assets_manual.delay(instance, username)


@receiver(m2m_changed, sender=SystemUser.nodes.through)
@on_transaction_commit
def on_system_user_nodes_change(sender, instance=None, action=None, model=None, pk_set=None, **kwargs):
    """
    当系统用户和节点关系发生变化时，应该将节点下资产关联到新的系统用户上
    """
    if action != POST_ADD:
        return
    logger.info("System user nodes update signal recv: {}".format(instance))

    queryset = model.objects.filter(pk__in=pk_set)
    if model == Node:
        nodes_keys = queryset.values_list('key', flat=True)
        system_users = [instance]
    else:
        nodes_keys = [instance.key]
        system_users = queryset
    add_nodes_assets_to_system_users.delay(nodes_keys, system_users)


@receiver(m2m_changed, sender=SystemUser.groups.through)
def on_system_user_groups_change(instance, action, pk_set, reverse, **kwargs):
    """
    当系统用户和用户组关系发生变化时，应该将组下用户关联到新的系统用户上
    """
    if action != POST_ADD:
        return
    if reverse:
        raise M2MReverseNotAllowed
    logger.info("System user groups update signal recv: {}".format(instance))

    users = User.objects.filter(groups__id__in=pk_set).distinct()
    instance.users.add(*users)


@receiver(post_save, sender=SystemUser, dispatch_uid="jms")
@on_transaction_commit
def on_system_user_update(instance: SystemUser, created, **kwargs):
    """
    当系统用户更新时，可能更新了密钥，用户名等，这时要自动推送系统用户到资产上,
    其实应该当 用户名，密码，密钥 sudo等更新时再推送，这里偷个懒,
    这里直接取了 instance.assets 因为nodes和系统用户发生变化时，会自动将nodes下的资产
    关联到上面
    """
    if instance and not created:
        logger.info("System user update signal recv: {}".format(instance))
        assets = instance.assets.all().valid()
        push_system_user_to_assets.delay(instance.id, [_asset.id for _asset in assets])
        # add assets to su_from
        instance.add_related_assets_to_su_from_if_need(assets)
