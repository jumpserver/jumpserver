# -*- coding: utf-8 -*-
#
from collections import defaultdict
from django.db.models.signals import post_save, m2m_changed, post_delete
from django.dispatch import receiver

from common.utils import get_logger
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


def set_asset_root_node(asset):
    logger.debug("Set asset default node: {}".format(Node.root()))
    asset.nodes.add(Node.root())


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
def on_asset_created_or_update(sender, instance=None, created=False, **kwargs):
    if created:
        logger.info("Asset `{}` create signal received".format(instance))
        update_asset_hardware_info_on_created(instance)
        test_asset_conn_on_created(instance)

        # 过期节点资产数量
        nodes = instance.nodes.all()
        Node.expire_nodes_assets_amount(nodes)


@receiver(post_delete, sender=Asset, dispatch_uid="my_unique_identifier")
def on_asset_delete(sender, instance=None, **kwargs):
    # 过期节点资产数量
    nodes = instance.nodes.all()
    Node.expire_nodes_assets_amount(nodes)


@receiver(post_save, sender=SystemUser, dispatch_uid="my_unique_identifier")
def on_system_user_update(sender, instance=None, created=True, **kwargs):
    if instance and not created:
        logger.info("System user `{}` update signal received".format(instance))
        assets = instance.assets.all()
        push_system_user_to_assets.delay(instance, assets)


@receiver(m2m_changed, sender=SystemUser.nodes.through)
def on_system_user_nodes_change(sender, instance=None, **kwargs):
    if instance and kwargs["action"] == "post_add":
        assets = set()
        nodes = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
        for node in nodes:
            assets.update(set(node.get_all_assets()))
        instance.assets.add(*tuple(assets))


@receiver(m2m_changed, sender=SystemUser.assets.through)
def on_system_user_assets_change(sender, instance=None, **kwargs):
    if instance and kwargs["action"] == "post_add":
        assets = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
        push_system_user_to_assets.delay(instance, assets)


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_asset_node_changed(sender, instance=None, **kwargs):
    logger.debug("Asset nodes change signal received")
    if isinstance(instance, Asset):
        if kwargs['action'] == 'pre_remove':
            nodes = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
            Node.expire_nodes_assets_amount(nodes)
        if kwargs['action'] == 'post_add':
            nodes = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
            Node.expire_nodes_assets_amount(nodes)
            system_users_assets = defaultdict(set)
            system_users = SystemUser.objects.filter(nodes__in=nodes)
            # 清理节点缓存
            for system_user in system_users:
                system_users_assets[system_user].update({instance})
            for system_user, assets in system_users_assets.items():
                system_user.assets.add(*tuple(assets))


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_node_assets_changed(sender, instance=None, **kwargs):
    if isinstance(instance, Node):
        logger.debug("Node assets change signal {} received".format(instance))
        # 当节点和资产关系发生改变时，过期资产数量缓存
        instance.expire_assets_amount()
        assets = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
        if kwargs['action'] == 'post_add':
            # 重新关联系统用户和资产的关系
            system_users = SystemUser.objects.filter(nodes=instance)
            for system_user in system_users:
                system_user.assets.add(*tuple(assets))


@receiver(post_save, sender=Node)
def on_node_update_or_created(sender, instance=None, created=False, **kwargs):
    if instance and not created:
        instance.expire_full_value()


@receiver(post_save, sender=AuthBook)
def on_auth_book_created(sender, instance=None, created=False, **kwargs):
    if created:
        logger.debug('Receive create auth book object signal.')
        instance.set_version_and_latest()
