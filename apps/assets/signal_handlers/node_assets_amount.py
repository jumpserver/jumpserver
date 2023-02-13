# -*- coding: utf-8 -*-
#
from operator import add, sub

from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from assets.models import Asset, Node
from common.const.signals import PRE_ADD, POST_REMOVE, PRE_CLEAR
from common.decorators import on_transaction_commit, merge_delay_run
from common.utils import get_logger
from orgs.utils import tmp_to_org
from ..tasks import check_node_assets_amount_task

logger = get_logger(__file__)


@on_transaction_commit
@receiver(m2m_changed, sender=Asset.nodes.through)
def on_node_asset_change(sender, action, instance, reverse, pk_set, **kwargs):
    # 不允许 `pre_clear` ，因为该信号没有 `pk_set`
    # [官网](https://docs.djangoproject.com/en/3.1/ref/signals/#m2m-changed)
    refused = (PRE_CLEAR,)
    if action in refused:
        raise ValueError

    mapper = {PRE_ADD: add, POST_REMOVE: sub}
    if action not in mapper:
        return

    with tmp_to_org(instance.org):
        if reverse:
            node_ids = [instance.id]
        else:
            node_ids = pk_set
        update_nodes_assets_amount(node_ids=node_ids)


@merge_delay_run(ttl=5)
def update_nodes_assets_amount(node_ids=()):
    nodes = list(Node.objects.filter(id__in=node_ids))
    logger.debug('Recv asset nodes change signal, recompute node assets amount')
    logger.info('Update nodes assets amount: {} nodes'.format(len(node_ids)))

    if len(node_ids) > 100:
        check_node_assets_amount_task.delay()
        return

    for node in nodes:
        node.assets_amount = node.get_assets_amount()

    Node.objects.bulk_update(nodes, ['assets_amount'])
