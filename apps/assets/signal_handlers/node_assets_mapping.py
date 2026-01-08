# -*- coding: utf-8 -*-
#

from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from assets.models import Asset
from common.utils import get_logger
from common.decorators import merge_delay_run

logger = get_logger(__name__)


@merge_delay_run(ttl=5)
def expire_node_asset_relation_cache(ignore_args=()):
    from assets.tree.node_tree import relation
    logger.debug('Expire Node-Asset relation cache')
    relation.update_nid_aids_mapper_if_needed()


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_node_asset_change(**kwargs):
    from assets.tree.node_tree import relation
    relation.clear_cache()
    expire_node_asset_relation_cache.delay()
