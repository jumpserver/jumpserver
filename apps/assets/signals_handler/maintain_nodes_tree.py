# -*- coding: utf-8 -*-
#
import os
import threading

from django.db.models.signals import (
    m2m_changed, post_save, post_delete
)
from django.dispatch import receiver
from django.utils.functional import LazyObject

from common.signals import django_ready
from common.utils.connection import RedisPubSub
from common.utils import get_logger
from assets.models import Asset, Node


logger = get_logger(__file__)

# clear node assets mapping for memory
# ------------------------------------


def get_node_assets_mapping_for_memory_pub_sub():
    return RedisPubSub('fm.node_all_assets_id_memory_mapping')


class NodeAssetsMappingForMemoryPubSub(LazyObject):
    def _setup(self):
        self._wrapped = get_node_assets_mapping_for_memory_pub_sub()


node_assets_mapping_for_memory_pub_sub = NodeAssetsMappingForMemoryPubSub()


def expire_node_assets_mapping_for_memory(org_id):
    # 所有进程清除(自己的 memory 数据)
    org_id = str(org_id)
    node_assets_mapping_for_memory_pub_sub.publish(org_id)
    # 当前进程清除(cache 数据)
    logger.debug(
        "Expire node assets id mapping from cache of org={}, pid={}"
        "".format(org_id, os.getpid())
    )
    Node.expire_node_all_assets_id_mapping_from_cache(org_id)


@receiver(post_save, sender=Node)
def on_node_post_create(sender, instance, created, update_fields, **kwargs):
    if created:
        need_expire = True
    elif update_fields and 'key' in update_fields:
        need_expire = True
    else:
        need_expire = False

    if need_expire:
        expire_node_assets_mapping_for_memory(instance.org_id)


@receiver(post_delete, sender=Node)
def on_node_post_delete(sender, instance, **kwargs):
    expire_node_assets_mapping_for_memory(instance.org_id)


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_node_asset_change(sender, instance, **kwargs):
    expire_node_assets_mapping_for_memory(instance.org_id)


@receiver(django_ready)
def subscribe_node_assets_mapping_expire(sender, **kwargs):
    logger.debug("Start subscribe for expire node assets id mapping from memory")

    def keep_subscribe():
        subscribe = node_assets_mapping_for_memory_pub_sub.subscribe()
        for message in subscribe.listen():
            if message["type"] != "message":
                continue
            org_id = message['data'].decode()
            Node.expire_node_all_assets_id_mapping_from_memory(org_id)
            logger.debug(
                "Expire node assets id mapping from memory of org={}, pid={}"
                "".format(str(org_id), os.getpid())
            )
    t = threading.Thread(target=keep_subscribe)
    t.daemon = True
    t.start()
