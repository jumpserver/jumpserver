# -*- coding: utf-8 -*-
#
from operator import add, sub

from django.conf import settings
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from assets.models import Asset, Node
from common.const.signals import PRE_CLEAR, POST_ADD, PRE_REMOVE
from common.decorators import on_transaction_commit, merge_delay_run
from common.signals import django_ready
from common.utils import get_logger
from orgs.utils import tmp_to_org, tmp_to_root_org
from ..tasks import check_node_assets_amount_task

logger = get_logger(__file__)


@receiver(m2m_changed, sender=Asset.nodes.through)
@on_transaction_commit
def on_node_asset_change(sender, action, instance, reverse, pk_set, **kwargs):
    # 不允许 `pre_clear` ，因为该信号没有 `pk_set`
    # [官网](https://docs.djangoproject.com/en/3.1/ref/signals/#m2m-changed)
    refused = (PRE_CLEAR,)
    if action in refused:
        raise ValueError

    # 这里监听 post_add, pre_remove, 如果pre_add 和 post_remove, 那么 node_ids 就已经获取不到了
    mapper = {POST_ADD: add, PRE_REMOVE: sub}
    if action not in mapper:
        return

    with tmp_to_org(instance.org):
        if reverse:
            node_ids = [instance.id]
        else:
            node_ids = list(pk_set)
        update_nodes_assets_amount.delay(node_ids=node_ids)


@merge_delay_run(ttl=30)
def update_nodes_assets_amount(node_ids=()):
    nodes = Node.objects.filter(id__in=node_ids)
    nodes = Node.get_ancestor_queryset(nodes)
    logger.debug('Recv asset nodes change signal, recompute node assets amount')
    logger.info('Update nodes assets amount: {} nodes'.format(len(node_ids)))

    if len(node_ids) > 100:
        check_node_assets_amount_task.delay()
        return

    for node in nodes:
        node.assets_amount = node.get_assets_amount()

    Node.objects.bulk_update(nodes, ['assets_amount'])


@receiver(django_ready)
def set_assets_size_to_setting(sender, **kwargs):
    from assets.models import Asset
    try:
        with tmp_to_root_org():
            amount = Asset.objects.order_by().count()
    except:
        amount = 0

    if amount > 20000:
        settings.ASSET_SIZE = 'large'
    elif amount > 2000:
        settings.ASSET_SIZE = 'medium'
