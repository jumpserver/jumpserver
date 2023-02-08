# -*- coding: utf-8 -*-
#
from django.db.models.signals import (
    post_save, m2m_changed, pre_delete, post_delete, pre_save
)
from django.dispatch import receiver
from django.utils.translation import gettext_noop

from assets.models import Asset, Node, Cloud, Device, Host, Web, Database
from assets.tasks import test_assets_connectivity_task
from common.const.signals import POST_ADD, POST_REMOVE, PRE_REMOVE
from common.decorators import on_transaction_commit, merge_delay_run
from common.utils import get_logger

logger = get_logger(__file__)


@receiver(pre_save, sender=Node)
def on_node_pre_save(sender, instance: Node, **kwargs):
    instance.parent_key = instance.compute_parent_key()


@merge_delay_run(ttl=10)
def test_assets_connectivity_handler(*assets):
    task_name = gettext_noop("Test assets connectivity ")
    test_assets_connectivity_task.delay(assets, task_name)


@merge_delay_run(ttl=10)
def gather_assets_facts_handler(*assets):
    pass


@receiver(post_save, sender=Asset)
@on_transaction_commit
def on_asset_create(sender, instance=None, created=False, **kwargs):
    """
    当资产创建时，更新硬件信息，更新可连接性
    确保资产必须属于一个节点
    """
    if not created:
        return
    logger.info("Asset create signal recv: {}".format(instance))

    # 获取资产硬件信息
    test_assets_connectivity_handler([instance])
    gather_assets_facts_handler([instance])

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


RELATED_NODE_IDS = '_related_node_ids'


@receiver(pre_delete, sender=Asset)
def on_asset_delete(instance: Asset, using, **kwargs):
    logger.debug("Asset pre delete signal recv: {}".format(instance))
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
    logger.debug("Asset delete signal recv: {}".format(instance))
    node_ids = getattr(instance, RELATED_NODE_IDS, None)
    if node_ids:
        m2m_changed.send(
            sender=Asset.nodes.through, instance=instance, reverse=False,
            model=Node, pk_set=node_ids, using=using, action=POST_REMOVE
        )


@on_transaction_commit
def resend_to_asset_signals(sender, signal, instance, **kwargs):
    signal.send(sender=Asset, instance=instance.asset_ptr, **kwargs)


for model in (Host, Database, Device, Web, Cloud):
    for s in (pre_save, post_save):
        s.connect(resend_to_asset_signals, sender=model)
