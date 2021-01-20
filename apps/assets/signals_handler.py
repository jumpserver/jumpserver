# -*- coding: utf-8 -*-
#
from operator import add, sub
from itertools import chain

from assets.utils import is_asset_exists_in_node
from django.db.models.signals import (
    post_save, m2m_changed, pre_delete, post_delete, pre_save
)
from django.db.models import Q, F
from django.dispatch import receiver

from common.exceptions import M2MReverseNotAllowed
from common.const.signals import PRE_ADD, POST_ADD, POST_REMOVE, PRE_CLEAR, PRE_REMOVE
from common.utils import get_logger
from common.decorator import on_transaction_commit
from .models import Asset, SystemUser, Node, compute_parent_key, NodeAssetRelatedRecord
from users.models import User
from .tasks import (
    update_assets_hardware_info_util,
    test_asset_connectivity_util,
    push_system_user_to_assets_manual,
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


@receiver(post_save, sender=SystemUser, dispatch_uid="jms")
@on_transaction_commit
def on_system_user_update(instance: SystemUser, created, **kwargs):
    """
    当系统用户更新时，可能更新了秘钥，用户名等，这时要自动推送系统用户到资产上,
    其实应该当 用户名，密码，秘钥 sudo等更新时再推送，这里偷个懒,
    这里直接取了 instance.assets 因为nodes和系统用户发生变化时，会自动将nodes下的资产
    关联到上面
    """
    if instance and not created:
        logger.info("System user update signal recv: {}".format(instance))
        assets = instance.assets.all().valid()
        push_system_user_to_assets.delay(instance.id, [_asset.id for _asset in assets])


@receiver(m2m_changed, sender=SystemUser.assets.through)
@on_transaction_commit
def on_system_user_assets_change(instance, action, model, pk_set, **kwargs):
    """
    当系统用户和资产关系发生变化时，应该重新推送系统用户到新添加的资产中
    """
    if action != POST_ADD:
        return
    logger.debug("System user assets change signal recv: {}".format(instance))
    if model == Asset:
        system_users_id = [instance.id]
        assets_id = pk_set
    else:
        system_users_id = pk_set
        assets_id = [instance.id]
    for system_user_id in system_users_id:
        push_system_user_to_assets.delay(system_user_id, assets_id)


@receiver(m2m_changed, sender=SystemUser.users.through)
@on_transaction_commit
def on_system_user_users_change(sender, instance: SystemUser, action, model, pk_set, reverse, **kwargs):
    """
    当系统用户和用户关系发生变化时，应该重新推送系统用户资产中
    """
    if action != POST_ADD:
        return

    if reverse:
        raise M2MReverseNotAllowed

    if not instance.username_same_with_user:
        return

    logger.debug("System user users change signal recv: {}".format(instance))
    usernames = model.objects.filter(pk__in=pk_set).values_list('username', flat=True)

    for username in usernames:
        push_system_user_to_assets_manual.delay(instance, username)


@receiver(m2m_changed, sender=SystemUser.nodes.through)
@on_transaction_commit
def on_system_user_nodes_change(sender, instance=None, action=None, model=None, pk_set=None, **kwargs):
    """
    当系统用户和节点关系发生变化时，应该将节点下资产关联到新的系统用户上
    """
    if action != POST_ADD:
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


@receiver(m2m_changed, sender=SystemUser.groups.through)
def on_system_user_groups_change(instance, action, pk_set, reverse, **kwargs):
    """
    当系统用户和用户组关系发生变化时，应该将组下用户关联到新的系统用户上
    """
    if action != POST_ADD:
        return
    if reverse:
        raise M2MReverseNotAllowed
    logger.info("System user groups update signal recv: {}".format(instance))

    users = User.objects.filter(groups__id__in=pk_set).distinct()
    instance.users.add(*users)


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
        push_system_user_to_assets.delay(system_user_id, asset_ids_to_push)
    m2m_model.objects.bulk_create(to_create)


def _update_node_assets_amount(node: Node, asset_pk_set: set, operator=add):
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


def _remove_ancestor_keys(ancestor_key, tree_set):
    # 这里判断 `ancestor_key` 不能是空，防止数据错误导致的死循环
    # 判断是否在集合里，来区分是否已被处理过
    while ancestor_key and ancestor_key in tree_set:
        tree_set.remove(ancestor_key)
        ancestor_key = compute_parent_key(ancestor_key)


def _update_nodes_asset_amount(node_keys, asset_pk, operator):
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
        exists = is_asset_exists_in_node(asset_pk, key)
        parent_key = compute_parent_key(key)

        if exists:
            # 如果资产在该节点，那么他及其祖先节点都不用处理
            _remove_ancestor_keys(parent_key, ancestor_keys)
            continue
        else:
            # 不存在，要更新本节点
            to_update_keys.append(key)
            # 这里判断 `parent_key` 不能是空，防止数据错误导致的死循环
            # 判断是否在集合里，来区分是否已被处理过
            while parent_key and parent_key in ancestor_keys:
                exists = is_asset_exists_in_node(asset_pk, parent_key)
                if exists:
                    _remove_ancestor_keys(parent_key, ancestor_keys)
                    break
                else:
                    to_update_keys.append(parent_key)
                    ancestor_keys.remove(parent_key)
                    parent_key = compute_parent_key(parent_key)

    Node.objects.filter(key__in=to_update_keys).update(
        assets_amount=operator(F('assets_amount'), 1)
    )


@receiver(m2m_changed, sender=Asset.nodes.through)
def update_nodes_assets_amount(action, instance, reverse, pk_set, **kwargs):
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
        _update_node_assets_amount(node, asset_pk_set, operator)
    else:
        asset_pk = instance.id
        # 与资产直接关联的节点
        node_keys = set(Node.objects.filter(id__in=pk_set).values_list('key', flat=True))
        _update_nodes_asset_amount(node_keys, asset_pk, operator)


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


@receiver(m2m_changed, sender=Asset.nodes.through)
def update_nodes_assets_related_record(sender, action, instance, reverse, pk_set, **kwargs):
    if reverse:
        node_ids = [instance.id]
        asset_ids = pk_set
    else:
        asset_ids = [instance.id]
        node_ids = pk_set

    if action == POST_ADD:
        record_related(asset_ids, node_ids, add)
    elif action == POST_REMOVE:
        record_related(asset_ids, node_ids, sub)


def record_related(asset_ids, node_ids, operator):
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

    delta = len(asset_ids)
    for key in chain(node_keys, ancestor_keys):
        node_id = key_id_mapper[key]
        for asset_id in asset_ids:
            record = records_mapper.get((asset_id, node_id))
            if record:
                record.related_count = operator(record.related_count, delta)
            else:
                record = NodeAssetRelatedRecord(node_id=node_id, asset_id=asset_id, related_count=operator(0, delta))
                to_create_records.append(record)
                records_mapper[(asset_id, node_id)] = record

    NodeAssetRelatedRecord.objects.bulk_create(to_create_records)
    NodeAssetRelatedRecord.objects.bulk_update(records, fields=('related_count', ))
