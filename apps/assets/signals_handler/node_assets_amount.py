# -*- coding: utf-8 -*-
#
from operator import add, sub
from django.db.models import Q, F
from django.dispatch import receiver
from django.db.models.signals import (
    m2m_changed
)

from orgs.utils import ensure_in_real_or_default_org
from common.const.signals import PRE_ADD, POST_REMOVE, PRE_CLEAR
from common.utils import get_logger
from assets.models import Asset, Node, compute_parent_key
from assets.locks import NodeTreeUpdateLock


logger = get_logger(__file__)


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_node_asset_change(sender, action, instance, reverse, pk_set, **kwargs):
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
        NodeAssetsAmountUtils.update_node_assets_amount(node, asset_pk_set, operator)
    else:
        asset_pk = instance.id
        # 与资产直接关联的节点
        node_keys = set(Node.objects.filter(id__in=pk_set).values_list('key', flat=True))
        NodeAssetsAmountUtils.update_nodes_asset_amount(node_keys, asset_pk, operator)


class NodeAssetsAmountUtils:

    @classmethod
    def _remove_ancestor_keys(cls, ancestor_key, tree_set):
        # 这里判断 `ancestor_key` 不能是空，防止数据错误导致的死循环
        # 判断是否在集合里，来区分是否已被处理过
        while ancestor_key and ancestor_key in tree_set:
            tree_set.remove(ancestor_key)
            ancestor_key = compute_parent_key(ancestor_key)

    @classmethod
    def _is_asset_exists_in_node(cls, asset_pk, node_key):
        exists = Asset.objects.filter(
            Q(nodes__key__istartswith=f'{node_key}:') | Q(nodes__key=node_key)
        ).filter(id=asset_pk).exists()
        return exists

    @classmethod
    @ensure_in_real_or_default_org
    @NodeTreeUpdateLock()
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
    @ensure_in_real_or_default_org
    @NodeTreeUpdateLock()
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
