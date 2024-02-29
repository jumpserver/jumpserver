# -*- coding: utf-8 -*-
#
from django.db.models.signals import (
    m2m_changed, pre_delete, post_delete, pre_save, post_save
)
from django.dispatch import receiver
from django.utils.translation import gettext_noop

from assets.models import Asset, Node, Host, Database, Device, Web, Cloud
from assets.tasks import test_assets_connectivity_task, gather_assets_facts_task
from common.const.signals import POST_REMOVE, PRE_REMOVE
from common.decorators import on_transaction_commit, merge_delay_run, key_by_org
from common.utils import get_logger
from orgs.utils import current_org

logger = get_logger(__file__)


@receiver(pre_save, sender=Node)
def on_node_pre_save(sender, instance: Node, **kwargs):
    instance.parent_key = instance.compute_parent_key()


@merge_delay_run(ttl=5, key=key_by_org)
def test_assets_connectivity_handler(assets=()):
    task_name = gettext_noop("Test assets connectivity ")
    asset_ids = [a.id for a in assets]
    test_assets_connectivity_task.delay(asset_ids, str(current_org.id), task_name)


@merge_delay_run(ttl=5, key=key_by_org)
def gather_assets_facts_handler(assets=()):
    if not assets:
        logger.info("No assets to update hardware info")
        return
    name = gettext_noop("Gather asset hardware info")
    asset_ids = [a.id for a in assets]
    gather_assets_facts_task.delay(asset_ids, str(current_org.id), task_name=name)


@merge_delay_run(ttl=5, key=key_by_org)
def ensure_asset_has_node(assets=()):
    asset_ids = [asset.id for asset in assets]
    has_ids = Asset.nodes.through.objects \
        .filter(asset_id__in=asset_ids) \
        .values_list('asset_id', flat=True)
    need_ids = set(asset_ids) - set(has_ids)
    if not need_ids:
        return

    org_root = Node.org_root()
    org_root.assets.add(*need_ids)


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

    ensure_asset_has_node.delay(assets=(instance,))

    # 获取资产硬件信息
    auto_config = instance.auto_config
    if auto_config.get('ping_enabled'):
        logger.debug('Asset {} ping enabled, test connectivity'.format(instance.name))
        test_assets_connectivity_handler.delay(assets=(instance,))
    if auto_config.get('gather_facts_enabled'):
        logger.debug('Asset {} gather facts enabled, gather facts'.format(instance.name))
        gather_assets_facts_handler(assets=(instance,))


RELATED_NODE_IDS = '_related_node_ids'


@receiver(pre_delete, sender=Asset)
def on_asset_delete(instance: Asset, using, **kwargs):
    node_ids = Node.objects.filter(assets=instance) \
        .distinct().values_list('id', flat=True)
    node_ids = list(node_ids)
    logger.debug("Asset pre delete signal recv: {}, node_ids: {}".format(instance, node_ids))
    setattr(instance, RELATED_NODE_IDS, list(node_ids))
    m2m_changed.send(
        sender=Asset.nodes.through, instance=instance,
        reverse=False, model=Node, pk_set=node_ids,
        using=using, action=PRE_REMOVE
    )


@receiver(post_delete, sender=Asset)
def on_asset_post_delete(instance: Asset, using, **kwargs):
    node_ids = getattr(instance, RELATED_NODE_IDS, [])
    logger.debug("Asset post delete signal recv: {}, node_ids: {}".format(instance, node_ids))
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
