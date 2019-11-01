# -*- coding: utf-8 -*-
#
from collections import defaultdict
from django.db.models.signals import (
    post_save, m2m_changed, post_delete
)
from django.db.models.aggregates import Count
from django.dispatch import receiver

from common.utils import get_logger, timeit
from common.decorator import on_transaction_commit
from .models import Asset, SystemUser, Node, AuthBook
from .tasks import (
    update_assets_hardware_info_util,
    test_asset_connectivity_util,
    push_system_user_to_assets,
    add_nodes_assets_to_system_users
)


logger = get_logger(__file__)


def update_asset_hardware_info_on_created(asset):
    logger.debug("Update asset `{}` hardware info".format(asset))
    update_assets_hardware_info_util.delay([asset])


def test_asset_conn_on_created(asset):
    logger.debug("Test asset `{}` connectivity".format(asset))
    test_asset_connectivity_util.delay([asset])


@receiver(post_save, sender=Asset)
@on_transaction_commit
def on_asset_created_or_update(sender, instance=None, created=False, **kwargs):
    """
    当资产创建时，更新硬件信息，更新可连接性
    确保资产必须属于一个节点
    """
    if created:
        logger.info("Asset create signal recv: {}".format(instance))

        # 获取资产硬件信息
        update_asset_hardware_info_on_created(instance)
        test_asset_conn_on_created(instance)

        # 确保资产存在一个节点
        has_node = instance.nodes.all().exists()
        if not has_node:
            instance.nodes.add(Node.org_root())


@receiver(post_delete, sender=Asset)
def on_asset_delete(sender, instance=None, **kwargs):
    """
    当资产删除时，刷新节点，节点中存在节点和资产的关系
    """
    logger.debug("Asset delete signal recv: {}".format(instance))
    Node.refresh_assets()


@receiver(post_save, sender=SystemUser, dispatch_uid="jms")
def on_system_user_update(sender, instance=None, created=True, **kwargs):
    """
    当系统用户更新时，可能更新了秘钥，用户名等，这时要自动推送系统用户到资产上,
    其实应该当 用户名，密码，秘钥 sudo等更新时再推送，这里偷个懒,
    这里直接取了 instance.assets 因为nodes和系统用户发生变化时，会自动将nodes下的资产
    关联到上面
    """
    if instance and not created:
        logger.info("System user update signal recv: {}".format(instance))
        assets = instance.assets.all().valid()
        push_system_user_to_assets.delay(instance, assets)


@receiver(m2m_changed, sender=SystemUser.assets.through)
def on_system_user_assets_change(sender, instance=None, action='', model=None, pk_set=None, **kwargs):
    """
    当系统用户和资产关系发生变化时，应该重新推送系统用户到新添加的资产中
    """
    if action != "post_add":
        return
    logger.debug("System user assets change signal recv: {}".format(instance))
    queryset = model.objects.filter(pk__in=pk_set)
    if model == Asset:
        system_users = [instance]
        assets = queryset
    else:
        system_users = queryset
        assets = [instance]
    for system_user in system_users:
        push_system_user_to_assets.delay(system_user, assets)


@receiver(m2m_changed, sender=SystemUser.nodes.through)
def on_system_user_nodes_change(sender, instance=None, action=None, model=None, pk_set=None, **kwargs):
    """
    当系统用户和节点关系发生变化时，应该将节点下资产关联到新的系统用户上
    """
    if action != "post_add":
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


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_asset_nodes_change(sender, instance=None, action='', **kwargs):
    """
    资产节点发生变化时，刷新节点
    """
    if action.startswith('post'):
        logger.debug("Asset nodes change signal recv: {}".format(instance))
        Node.refresh_assets()


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_asset_nodes_add(sender, instance=None, action='', model=None, pk_set=None, **kwargs):
    """
    当资产的节点发生变化时，或者 当节点的资产关系发生变化时，
    节点下新增的资产，添加到节点关联的系统用户中
    """
    if action != "post_add":
        return
    logger.debug("Assets node add signal recv: {}".format(action))
    queryset = model.objects.filter(pk__in=pk_set).values_list('id', flat=True)
    if model == Node:
        nodes = queryset
        assets = [instance]
    else:
        nodes = [instance]
        assets = queryset
    # 节点资产发生变化时，将资产关联到节点关联的系统用户, 只关注新增的
    system_users_assets = defaultdict(set)
    system_users = SystemUser.objects.filter(nodes__in=nodes)
    for system_user in system_users:
        system_users_assets[system_user].update(set(assets))
    for system_user, _assets in system_users_assets.items():
        system_user.assets.add(*tuple(_assets))


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_asset_nodes_remove(sender, instance=None, action='', model=None,
                          pk_set=None, **kwargs):

    """
    监控资产删除节点关系, 或节点删除资产，避免产生游离资产
    """
    if action not in ["post_remove", "pre_clear", "post_clear"]:
        return
    if action == "pre_clear":
        if model == Node:
            instance._nodes = list(instance.nodes.all())
        else:
            instance._assets = list(instance.assets.all())
        return
    logger.debug("Assets node remove signal recv: {}".format(action))
    if action == "post_remove":
        queryset = model.objects.filter(pk__in=pk_set)
    else:
        if model == Node:
            queryset = instance._nodes
        else:
            queryset = instance._assets
    if model == Node:
        assets = [instance]
    else:
        assets = queryset
    if isinstance(assets, list):
        assets_not_has_node = []
        for asset in assets:
            if asset.nodes.all().count() == 0:
                assets_not_has_node.append(asset.id)
    else:
        assets_not_has_node = assets.annotate(nodes_count=Count('nodes'))\
            .filter(nodes_count=0).values_list('id', flat=True)
    Node.org_root().assets.add(*tuple(assets_not_has_node))


@receiver([post_save, post_delete], sender=Node)
def on_node_update_or_created(sender, **kwargs):
    # 刷新节点
    Node.refresh_nodes()


@receiver(post_save, sender=AuthBook)
def on_authbook_created(sender, instance=None, created=True, **kwargs):
    if created and instance:
        instance.set_version()
