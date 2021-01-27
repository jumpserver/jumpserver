# -*- coding: utf-8 -*-
#
import os
import threading
from operator import add, sub
from itertools import chain

from django.db.models.signals import (
    m2m_changed, post_save, post_delete
)
from django.db.models import Q, F
from django.dispatch import receiver
from django.utils.functional import LazyObject

from common.signals import django_ready
from common.utils.connection import RedisPubSub
from orgs.utils import ensure_in_real_or_default_org
from common.const.signals import PRE_ADD, POST_ADD, POST_REMOVE, PRE_CLEAR
from common.utils import get_logger
from assets.models import Asset, Node, compute_parent_key, NodeAssetRelatedRecord
from assets.locks import NodeTreeUpdateLock


logger = get_logger(__file__)


class MaintainNodesAssetsTree:

    @classmethod
    def _remove_ancestor_keys(cls, ancestor_key, tree_set):
        # 这里判断 `ancestor_key` 不能是空，防止数据错误导致的死循环
        # 判断是否在集合里，来区分是否已被处理过
        while ancestor_key and ancestor_key in tree_set:
            tree_set.remove(ancestor_key)
            ancestor_key = compute_parent_key(ancestor_key)

    @classmethod
    def do_node_assets_amount(cls, sender, action, instance, reverse, pk_set, **kwargs):
        # 不允许 `pre_clear` ，因为该信号没有 `pk_set`
        # [官网](https://docs.djangoproject.com/en/3.1/ref/signals/#m2m-changed)
        refused = (PRE_CLEAR,)
        if action in refused:
            raise ValueError

        mapper = {
            PRE_ADD: add,
            POST_REMOVE: sub
        }
        if action not in mapper:
            return

        operator = mapper[action]

        if reverse:
            node: Node = instance
            asset_pk_set = set(pk_set)
            cls.update_node_assets_amount(node, asset_pk_set, operator)
        else:
            asset_pk = instance.id
            # 与资产直接关联的节点
            node_keys = set(Node.objects.filter(id__in=pk_set).values_list('key', flat=True))
            cls.update_nodes_asset_amount(node_keys, asset_pk, operator)

    @classmethod
    def do_related_record(cls, sender, action, instance, reverse, pk_set, **kwargs):
        if reverse:
            node_ids = [instance.id]
            asset_ids = pk_set
        else:
            asset_ids = [instance.id]
            node_ids = pk_set

        if action == POST_ADD:
            cls.record_related(asset_ids, node_ids, add)
        elif action == POST_REMOVE:
            cls.record_related(asset_ids, node_ids, sub)

    @classmethod
    def do(cls, **kwargs):
        ensure_in_real_or_default_org()
        with NodeTreeUpdateLock():
            cls.do_node_assets_amount(**kwargs)
            cls.do_related_record(**kwargs)

    @classmethod
    def record_related(cls, asset_ids, node_ids, operator):
        """
        asset_ids 加到或者离开 node_ids
        """

        nodes = Node.objects.filter(id__in=node_ids)
        node_keys = [n.key for n in nodes]

        ancestor_keys = []
        for key in node_keys:
            keys = Node.get_node_ancestor_keys(key)
            ancestor_keys.extend(keys)

        key_id_mapper = dict(Node.objects.filter(key__in=ancestor_keys).values_list('key', 'id'))
        key_id_mapper.update({n.key: n.id for n in nodes})

        records = NodeAssetRelatedRecord.objects.filter(asset_id__in=asset_ids, node_id__in=key_id_mapper.values())
        to_create_records = []

        records_mapper = {(r.asset_id, r.node_id): r for r in records}

        for key in chain(node_keys, ancestor_keys):
            node_id = key_id_mapper[key]
            for asset_id in asset_ids:
                record = records_mapper.get((asset_id, node_id))
                if record:
                    record.related_count = operator(record.related_count, 1)
                else:
                    record = NodeAssetRelatedRecord(node_id=node_id, asset_id=asset_id,
                                                    related_count=operator(0, 1))
                    to_create_records.append(record)
                    records_mapper[(asset_id, node_id)] = record

        NodeAssetRelatedRecord.objects.bulk_create(to_create_records)
        NodeAssetRelatedRecord.objects.bulk_update(records, fields=('related_count',))
        NodeAssetRelatedRecord.objects.filter(related_count__lt=1).delete()

    @classmethod
    def _is_asset_exists_in_node(cls, asset_pk, node_key):
        node = Node.objects.only('id').get(key=node_key)
        exists = NodeAssetRelatedRecord.objects.filter(asset_id=asset_pk, node_id=node.id).exists()
        return exists

    @classmethod
    def update_nodes_asset_amount(cls, node_keys, asset_pk, operator):
        """
        一个资产与多个节点关系变化时，更新计数

        :param node_keys: 节点 id 的集合
        :param asset_pk: 资产 id
        :param operator: 操作
        """

        # 所有相关节点的祖先节点，组成一棵局部树
        ancestor_keys = set()
        for key in node_keys:
            ancestor_keys.update(Node.get_node_ancestor_keys(key))

        # 相关节点可能是其他相关节点的祖先节点，如果是从相关节点里干掉
        node_keys -= ancestor_keys

        to_update_keys = []
        for key in node_keys:
            # 遍历相关节点，处理它及其祖先节点
            # 查询该节点是否包含待处理资产
            exists = cls._is_asset_exists_in_node(asset_pk, key)
            parent_key = compute_parent_key(key)

            if exists:
                # 如果资产在该节点，那么他及其祖先节点都不用处理
                cls._remove_ancestor_keys(parent_key, ancestor_keys)
                continue
            else:
                # 不存在，要更新本节点
                to_update_keys.append(key)
                # 这里判断 `parent_key` 不能是空，防止数据错误导致的死循环
                # 判断是否在集合里，来区分是否已被处理过
                while parent_key and parent_key in ancestor_keys:
                    exists = cls._is_asset_exists_in_node(asset_pk, parent_key)
                    if exists:
                        cls._remove_ancestor_keys(parent_key, ancestor_keys)
                        break
                    else:
                        to_update_keys.append(parent_key)
                        ancestor_keys.remove(parent_key)
                        parent_key = compute_parent_key(parent_key)

        Node.objects.filter(key__in=to_update_keys).update(
            assets_amount=operator(F('assets_amount'), 1)
        )

    @classmethod
    def update_node_assets_amount(cls, node: Node, asset_pk_set: set, operator=add):
        """
        一个节点与多个资产关系变化时，更新计数

        :param node: 节点实例
        :param asset_pk_set: 资产的`id`集合, 内部不会修改该值
        :param operator: 操作
        * -> Node
        # -> Asset

               * [3]
              / \
             *   * [2]
            /     \
           *       * [1]
          /       / \
         *   [a] #  # [b]

        """
        # 获取节点[1]祖先节点的 `key` 含自己，也就是[1, 2, 3]节点的`key`
        ancestor_keys = node.get_ancestor_keys(with_self=True)
        ancestors = Node.objects.filter(key__in=ancestor_keys).order_by('-key')
        to_update = []
        for ancestor in ancestors:
            # 迭代祖先节点的`key`，顺序是 [1] -> [2] -> [3]
            # 查询该节点及其后代节点是否包含要操作的资产，将包含的从要操作的
            # 资产集合中去掉，他们是重复节点，无论增加或删除都不会影响节点的资产数量

            asset_pk_set -= set(Asset.objects.filter(
                id__in=asset_pk_set
            ).filter(
                Q(nodes__key__istartswith=f'{ancestor.key}:') |
                Q(nodes__key=ancestor.key)
            ).distinct().values_list('id', flat=True))
            if not asset_pk_set:
                # 要操作的资产集合为空，说明都是重复资产，不用改变节点资产数量
                # 而且既然它包含了，它的祖先节点肯定也包含了，所以祖先节点都不用
                # 处理了
                break
            ancestor.assets_amount = operator(F('assets_amount'), len(asset_pk_set))
            to_update.append(ancestor)
        Node.objects.bulk_update(to_update, fields=('assets_amount', 'parent_key'))


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
    node_assets_mapping_for_memory_pub_sub.publish(org_id)
    # 当前进程清除(cache 数据)
    logger.debug(
        "Expire node assets id mapping from cache of org={}, pid={}"
        "".format(str(org_id), os.getpid())
    )
    Node.expire_node_all_assets_id_mapping_from_cache(org_id)


@receiver(post_save, sender=Node)
def on_node_post_create(sender, instance, created, update_fields, **kwargs):
    if created:
        _to_expire = True
    elif update_fields and 'key' in update_fields:
        _to_expire = True
    else:
        _to_expire = False

    if _to_expire:
        expire_node_assets_mapping_for_memory(instance.org_id)


@receiver(post_delete, sender=Node)
def on_node_post_delete(sender, instance, **kwargs):
    expire_node_assets_mapping_for_memory(instance.org_id)


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_node_asset_change(sender, instance, **kwargs):
    expire_node_assets_mapping_for_memory(instance.org_id)


@receiver(django_ready)
def subscribe_settings_change(sender, **kwargs):
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
