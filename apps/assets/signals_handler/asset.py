# -*- coding: utf-8 -*-
#
from django.db.models.signals import (
    post_save, m2m_changed, pre_delete, post_delete, pre_save
)
from django.dispatch import receiver

from common.const.signals import POST_ADD, POST_REMOVE, PRE_REMOVE
from common.utils import get_logger
from common.decorator import on_transaction_commit
from assets.models import Asset, SystemUser, Node
from assets.tasks import (
    update_assets_hardware_info_util,
    test_asset_connectivity_util,
    push_system_user_to_assets,
)

logger = get_logger(__file__)


def update_asset_hardware_info_on_created(asset):
    logger.debug("Update asset `{}` hardware info".format(asset))
    update_assets_hardware_info_util.delay([asset])


def test_asset_conn_on_created(asset):
    logger.debug("Test asset `{}` connectivity".format(asset))
    test_asset_connectivity_util.delay([asset])


@receiver(pre_save, sender=Node)
def on_node_pre_save(sender, instance: Node, **kwargs):
    instance.parent_key = instance.compute_parent_key()


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


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_asset_nodes_add(instance, action, reverse, pk_set, **kwargs):
    """
    本操作共访问 4 次数据库

    当资产的节点发生变化时，或者 当节点的资产关系发生变化时，
    节点下新增的资产，添加到节点关联的系统用户中
    """
    if action != POST_ADD:
        return
    logger.debug("Assets node add signal recv: {}".format(action))
    if reverse:
        nodes = [instance.key]
        asset_ids = pk_set
    else:
        nodes = Node.objects.filter(pk__in=pk_set).values_list('key', flat=True)
        asset_ids = [instance.id]

    # 节点资产发生变化时，将资产关联到节点及祖先节点关联的系统用户, 只关注新增的
    nodes_ancestors_keys = set()
    for node in nodes:
        nodes_ancestors_keys.update(Node.get_node_ancestor_keys(node, with_self=True))

    # 查询所有祖先节点关联的系统用户，都是要跟资产建立关系的
    system_user_ids = SystemUser.objects.filter(
        nodes__key__in=nodes_ancestors_keys
    ).distinct().values_list('id', flat=True)

    # 查询所有已存在的关系
    m2m_model = SystemUser.assets.through
    exist = set(m2m_model.objects.filter(
        systemuser_id__in=system_user_ids, asset_id__in=asset_ids
    ).values_list('systemuser_id', 'asset_id'))
    # TODO 优化
    to_create = []
    for system_user_id in system_user_ids:
        asset_ids_to_push = []
        for asset_id in asset_ids:
            if (system_user_id, asset_id) in exist:
                continue
            asset_ids_to_push.append(asset_id)
            to_create.append(m2m_model(
                systemuser_id=system_user_id,
                asset_id=asset_id
            ))
        if asset_ids_to_push:
            push_system_user_to_assets.delay(system_user_id, asset_ids_to_push)
    m2m_model.objects.bulk_create(to_create)


RELATED_NODE_IDS = '_related_node_ids'


@receiver(pre_delete, sender=Asset)
def on_asset_delete(instance: Asset, using, **kwargs):
    node_ids = set(Node.objects.filter(
        assets=instance
    ).distinct().values_list('id', flat=True))
    setattr(instance, RELATED_NODE_IDS, node_ids)
    m2m_changed.send(
        sender=Asset.nodes.through, instance=instance, reverse=False,
        model=Node, pk_set=node_ids, using=using, action=PRE_REMOVE
    )


@receiver(post_delete, sender=Asset)
def on_asset_post_delete(instance: Asset, using, **kwargs):
    node_ids = getattr(instance, RELATED_NODE_IDS, None)
    if node_ids:
        m2m_changed.send(
            sender=Asset.nodes.through, instance=instance, reverse=False,
            model=Node, pk_set=node_ids, using=using, action=POST_REMOVE
        )
