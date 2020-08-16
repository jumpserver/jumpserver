from functools import reduce
from operator import or_
from uuid import uuid4
import threading

from django.db.models import F, Count, Q, Value, BooleanField

from common.utils import get_logger
from common.const.distributed_lock_key import UPDATE_MAPPING_NODE_TASK_LOCK_KEY
from orgs.utils import tmp_to_root_org
from common.utils.timezone import dt_formater, now
from assets.models import Node, Asset
from django.db.transaction import atomic
from orgs import lock
from perms.models import UserGrantedMappingNode, RebuildUserTreeTask
from users.models import User

logger = get_logger(__name__)

ADD = 'add'
REMOVE = 'remove'


def get_granted_q(user: User):
    return (
            Q(granted_by_permissions__users=user) |
            Q(granted_by_permissions__user_groups__users=user)
    )


TMP_GRANTED_FIELD = '_granted'
TMP_ASSET_GRANTED_FIELD = '_asset_granted'
TMP_GRANTED_ASSET_AMOUNT = '_granted_asset_amount'


node_annotate_mapping_node = {
    TMP_GRANTED_FIELD: F('mapping_nodes__granted'),
    TMP_ASSET_GRANTED_FIELD: F('mapping_nodes__asset_granted'),
    TMP_GRANTED_ASSET_AMOUNT: F('mapping_nodes__assets_amount')
}


node_annotate_set_granted = {
    TMP_GRANTED_FIELD: Value(True, output_field=BooleanField()),
}


def is_granted(node):
    return getattr(node, TMP_GRANTED_FIELD, False)


def is_asset_granted(node):
    return getattr(node, TMP_ASSET_GRANTED_FIELD, False)


def get_granted_asset_amount(node):
    return getattr(node, TMP_GRANTED_ASSET_AMOUNT, 0)


def obj_field_add(obj, field, value=1):
    new_value = getattr(obj, field, 0) + value
    setattr(obj, field, new_value)


def set_granted(obj):
    setattr(obj, TMP_GRANTED_FIELD, True)


def set_asset_granted(obj):
    setattr(obj, TMP_ASSET_GRANTED_FIELD, True)


VALUE_TEMPLATE = '{stage}:{rand_str}:thread:{thread_name}:{thread_id}:{now}'


def _generate_value(stage=lock.DOING):
    cur_thread = threading.current_thread()

    return VALUE_TEMPLATE.format(
        stage=stage,
        thread_name=cur_thread.name,
        thread_id=cur_thread.ident,
        now=dt_formater(now()),
        rand_str=uuid4()
    )


def run_user_mapping_node_task(user: User):
    key = UPDATE_MAPPING_NODE_TASK_LOCK_KEY.format(user_id=user.id)
    doing_value = _generate_value()
    commiting_value = _generate_value(stage=lock.COMMITING)

    try:
        locked = lock.acquire(key, doing_value, timeout=60)
        if not locked:
            logger.error(f'update_mapping_node_task_locked_failed for user: {user.id}')
            raise lock.SomeoneIsDoingThis

        with atomic(savepoint=False):
            tasks = RebuildUserTreeTask.objects.filter(user=user)
            if tasks:
                rebuild_mapping_nodes(user)
                tasks.delete()
                ok = lock.change_lock_state_to_commiting(key, doing_value, commiting_value)
                if not ok:
                    logger.error(f'update_mapping_node_task_timeout for user: {user.id}')
                    raise lock.Timeout
    finally:
        lock.release(key, commiting_value, doing_value)


@tmp_to_root_org()
def compute_tmp_mapping_node_from_perm(user: User):
    node_only_fields = ('id', 'key', 'parent_key', 'assets_amount')

    # 查询直接授权节点
    nodes = Node.objects.filter(
        Q(granted_by_permissions__users=user) |
        Q(granted_by_permissions__user_groups__users=user)
    ).distinct().only(*node_only_fields)

    # 查询直接授权资产
    asset_ids = Asset.objects.filter(
        Q(granted_by_permissions__users=user) |
        Q(granted_by_permissions__user_groups__users=user)
    ).distinct().values_list('id', flat=True)

    key2leaf_nodes_mapper = {}

    # 给授权节点设置 _granted 标识，同时去重
    for _node in nodes:
        if _node.key not in key2leaf_nodes_mapper:
            set_granted(_node)
            key2leaf_nodes_mapper[_node.key] = _node

    # 查询授权资产关联的节点设置
    granted_asset_nodes = Node.objects.filter(
        assets__id__in=asset_ids
    ).only(*node_only_fields)

    # 给资产授权关联的节点设置 _asset_granted 标识，同时去重
    for _node in granted_asset_nodes:
        if _node.key not in key2leaf_nodes_mapper:
            key2leaf_nodes_mapper[_node.key] = _node
        set_asset_granted(key2leaf_nodes_mapper[_node.key])
    leaf_nodes = key2leaf_nodes_mapper.values()

    # 计算所有祖先节点
    ancestor_keys = set()
    for _node in leaf_nodes:
        ancestor_keys.update(_node.get_ancestor_keys())

    # 从祖先节点 key 中去掉同时也是叶子节点的 key
    ancestor_keys -= key2leaf_nodes_mapper.keys()
    # 查出祖先节点
    ancestors = Node.objects.filter(key__in=ancestor_keys).only(*node_only_fields)
    return [*key2leaf_nodes_mapper.values(), *ancestors]


def create_mapping_nodes(user, nodes, clear=True):
    to_create = []
    for node in nodes:
        _granted = getattr(node, TMP_GRANTED_FIELD, False)
        _asset_granted = getattr(node, TMP_ASSET_GRANTED_FIELD, False)
        _granted_asset_amount = getattr(node, TMP_GRANTED_ASSET_AMOUNT, 0)
        to_create.append(UserGrantedMappingNode(
            user=user,
            node=node,
            key=node.key,
            parent_key=node.parent_key,
            granted=_granted,
            asset_granted=_asset_granted,
            assets_amount=_granted_asset_amount,
        ))

    if clear:
        UserGrantedMappingNode.objects.filter(user=user).delete()
    UserGrantedMappingNode.objects.bulk_create(to_create)


def set_node_granted_asset_amount(user, node):
    """
    不依赖`UserGrantedMappingNode`直接查询授权计算资产数量
    """
    _granted = getattr(node, TMP_GRANTED_FIELD, False)
    if _granted:
        assets_amount = node.assets_amount
    else:
        assets_amount = count_node_all_granted_assets(user, node.key)
    setattr(node, TMP_GRANTED_ASSET_AMOUNT, assets_amount)


def rebuild_mapping_nodes(user):
    tmp_nodes = compute_tmp_mapping_node_from_perm(user)
    if True:  # TODO 这里可以配置
        for _node in tmp_nodes:
            set_node_granted_asset_amount(user, _node)
    create_mapping_nodes(user, tmp_nodes)


def get_node_all_granted_assets(user: User, key):
    """
    此算法依据 `UserGrantedMappingNode` 的数据查询
    1. 查询该节点下的直接授权节点
    2. 查询该节点下授权资产关联的节点
    """

    assets = Asset.objects.none()

    # 查询该节点下的授权节点
    granted_mapping_nodes = UserGrantedMappingNode.objects.filter(
        user=user,
        granted=True,
    ).filter(Q(key__startswith=f'{key}:') | Q(key=key))

    # 根据授权节点构建资产查询条件
    granted_nodes_qs = []
    for _node in granted_mapping_nodes:
        granted_nodes_qs.append(Q(nodes__key__startswith=f'{_node.key}:'))
        granted_nodes_qs.append(Q(nodes__key=_node.key))

    # 查询该节点下的资产授权节点
    only_asset_granted_mapping_nodes = UserGrantedMappingNode.objects.filter(
        user=user,
        asset_granted=True,
        granted=False,
    ).filter(Q(key__startswith=f'{key}:') | Q(key=key))

    # 根据资产授权节点构建查询
    only_asset_granted_nodes_qs = []
    for _node in only_asset_granted_mapping_nodes:
        only_asset_granted_nodes_qs.append(Q(nodes__id=_node.node_id))

    q = []
    if granted_nodes_qs:
        q.append(reduce(or_, granted_nodes_qs))

    if only_asset_granted_nodes_qs:
        only_asset_granted_nodes_q = reduce(or_, only_asset_granted_nodes_qs)
        only_asset_granted_nodes_q &= Q(granted_by_permissions__users=user) | Q(
            granted_by_permissions__user_groups__users=user)
        q.append(only_asset_granted_nodes_q)

    if q:
        assets = Asset.objects.filter(reduce(or_, q)).distinct()
    return assets


def get_node_all_granted_assets_from_perm(user: User, key):
    """
    此算法依据 `AssetPermission` 的数据查询
    1. 查询该节点下的直接授权节点
    2. 查询该节点下授权资产关联的节点
    """
    granted_q = get_granted_q(user)

    granted_nodes = Node.objects.filter(
        Q(key__startswith=f'{key}:') | Q(key=key)
    ).filter(granted_q)

    # 直接授权资产查询条件
    granted_asset_filter_q = (Q(nodes__key__startswith=f'{key}:') | Q(nodes__key=key)) & granted_q

    # 根据授权节点构建资产查询条件
    q = granted_asset_filter_q
    for _node in granted_nodes:
        q |= Q(nodes__key__startswith=f'{_node.key}:')
        q |= Q(nodes__key=_node.key)

    asset_qs = Asset.objects.filter(q)
    return asset_qs


def count_node_all_granted_assets(user: User, key):
    return get_node_all_granted_assets_from_perm(user, key).count()
