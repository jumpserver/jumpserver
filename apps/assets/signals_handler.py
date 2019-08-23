# -*- coding: utf-8 -*-
#
from collections import defaultdict
from django.db.models.signals import (
    post_save, m2m_changed, pre_delete, pre_save, pre_init, post_init
)
from django.dispatch import receiver

from common.utils import get_logger
from common.decorator import on_transaction_commit
from .models import Asset, SystemUser, Node, AuthBook
from .tasks import (
    update_assets_hardware_info_util,
    test_asset_connectivity_util,
    push_system_user_to_assets
)


logger = get_logger(__file__)


def update_asset_hardware_info_on_created(asset):
    logger.debug("Update asset `{}` hardware info".format(asset))
    update_assets_hardware_info_util.delay([asset])


def test_asset_conn_on_created(asset):
    logger.debug("Test asset `{}` connectivity".format(asset))
    test_asset_connectivity_util.delay([asset])


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
@on_transaction_commit
def on_asset_created_or_update(sender, instance=None, created=False, **kwargs):
    """
    当资产创建时，更新硬件信息，更新可连接性
    """
    if created:
        logger.info("Asset `{}` create signal received".format(instance))

        # 获取资产硬件信息
        update_asset_hardware_info_on_created(instance)
        test_asset_conn_on_created(instance)


@receiver(pre_delete, sender=Asset, dispatch_uid="my_unique_identifier")
def on_asset_delete(sender, instance=None, **kwargs):
    """
    当资产删除时，刷新节点，节点中存在节点和资产的关系
    """
    Node.refresh_nodes()


@receiver(post_save, sender=SystemUser, dispatch_uid="my_unique_identifier")
def on_system_user_update(sender, instance=None, created=True, **kwargs):
    """
    当系统用户更新时，可能更新了秘钥，用户名等，这时要自动推送系统用户到资产上,
    其实应该当 用户名，密码，秘钥 sudo等更新时再推送，这里偷个懒,
    这里直接取了 instance.assets 因为nodes和系统用户发生变化时，会自动将nodes下的资产
    关联到上面
    """
    if instance and not created:
        logger.info("System user `{}` update signal received".format(instance))
        assets = instance.assets.all().valid()
        push_system_user_to_assets.delay(instance, assets)


@receiver(m2m_changed, sender=SystemUser.assets.through, dispatch_uid="my_unique_identifier")
def on_system_user_assets_change(sender, instance=None, **kwargs):
    """
    当系统用户和资产关系发生变化时，应该重新推送系统用户到新添加的资产中
    """
    if instance and kwargs["action"] == "post_add":
        assets = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
        push_system_user_to_assets.delay(instance, assets)


@receiver(m2m_changed, sender=SystemUser.nodes.through, dispatch_uid="my_unique_identifier")
def on_system_user_nodes_change(sender, instance=None, **kwargs):
    """
    当系统用户和节点关系发生变化时，应该将节点关联到新的系统用户上
    """
    if instance and kwargs["action"] == "post_add":
        logger.info("System user `{}` nodes update signal received".format(instance))
        nodes_keys = kwargs['model'].objects.filter(
            pk__in=kwargs['pk_set']
        ).values_list('key', flat=True)
        assets = Node.get_nodes_all_assets(nodes_keys)
        instance.assets.add(*tuple(assets))


@receiver(m2m_changed, sender=Asset.nodes.through, dispatch_uid="my_unique_identifier")
def on_asset_nodes_changed(sender, instance=None, **kwargs):
    """
    当资产的节点发生变化时，或者 当节点的资产关系发生变化时，
    节点下新增的资产，添加到节点关联的系统用户中
    并刷新节点
    """
    if isinstance(instance, Asset):
        logger.debug("Asset nodes change signal received: {}".format(instance))
        # 节点资产发生变化时，将资产关联到节点关联的系统用户
        if kwargs['action'] == 'post_add':
            nodes = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
            system_users_assets = defaultdict(set)
            system_users = SystemUser.objects.filter(nodes__in=nodes)
            for system_user in system_users:
                system_users_assets[system_user].add(instance)
            for system_user, assets in system_users_assets.items():
                system_user.assets.add(*tuple(assets))
    if isinstance(instance, Node):
        logger.debug("Node assets change signal received: {}".format(instance))

    Node.refresh_nodes()


@receiver(post_save, sender=Node)
def on_node_update_or_created(sender, instance=None, created=False, **kwargs):
    # 刷新节点
    Node.refresh_nodes()


@receiver(post_save, sender=AuthBook)
def on_auth_book_created(sender, instance=None, created=False, **kwargs):
    if created:
        logger.debug('Receive create auth book object signal.')
        instance.set_version_and_latest()
