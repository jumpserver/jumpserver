from functools import reduce, wraps
from operator import or_
from uuid import uuid4
import threading
import inspect
from typing import List
from itertools import chain

from django.core.cache import cache
from django.conf import settings
from django.db.models import F, Q, Value, BooleanField
from django.utils.translation import ugettext_lazy as _

from .utils import Tree
from common.utils import timeit
from common.http import is_true
from common.utils import get_logger
from common.const.distributed_lock_key import UPDATE_MAPPING_NODE_TASK_LOCK_KEY
from orgs.utils import tmp_to_org
from common.utils.timezone import dt_formater, now
from assets.models import Node, Asset, FavoriteAsset, NodeAssetRelatedRecord
from django.db.transaction import atomic
from orgs import lock
from perms.models import UserGrantedMappingNode, RebuildUserTreeTask, AssetPermission
from users.models import User

logger = get_logger(__name__)

ADD = 'add'
REMOVE = 'remove'

UNGROUPED_NODE_KEY = 'ungrouped'
UNGROUPED_NODE_VALUE = _('Ungrouped')
FAVORITE_NODE_KEY = 'favorite'
FAVORITE_NODE_VALUE = _('Favorite')

TMP_GRANTED_FIELD = '_granted'
TMP_ASSET_GRANTED_FIELD = '_asset_granted'
TMP_GRANTED_ASSETS_AMOUNT_FIELD = '_granted_assets_amount'


# 使用场景
# `Node.objects.annotate(**node_annotate_mapping_node)`
node_annotate_mapping_node = {
    TMP_GRANTED_FIELD: F('mapping_nodes__granted'),
    TMP_ASSET_GRANTED_FIELD: F('mapping_nodes__asset_granted'),
    TMP_GRANTED_ASSETS_AMOUNT_FIELD: F('mapping_nodes__assets_amount')
}


# 使用场景
# `Node.objects.annotate(**node_annotate_set_granted)`
node_annotate_set_granted = {
    TMP_GRANTED_FIELD: Value(True, output_field=BooleanField()),
}


def is_direct_granted(node):
    return getattr(node, TMP_GRANTED_FIELD, False)


def is_asset_granted(node):
    return getattr(node, TMP_ASSET_GRANTED_FIELD, False)


def get_granted_assets_amount(node):
    return getattr(node, TMP_GRANTED_ASSETS_AMOUNT_FIELD, 0)


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


class UserPermTreeRefreshController:
    key_template = 'perms.tree.user.{user_id}'

    def __init__(self, user):
        self.user = user
        self.key = self.key_template.format({'user_id': user.id})
        self.client = cache.client.get_client(write=True)

    def get_need_refresh_org_ids(self):
        org_ids = self.client.smembers(self.key)
        return {org_id.decode() for org_id in org_ids}

    def add_need_refresh_org_ids(self, *org_ids):
        self.client.sadd(self.key, *org_ids)

    @classmethod
    def add_need_refresh_orgs_for_users(cls, org_ids, user_ids):
        client = cache.client.get_client(write=True)

        with client.pipeline(transaction=False) as p:
            for user_id in user_ids:
                key = cls.key_template.format({'user_id': user_id})
                p.sadd(key, *org_ids)

            p.execute()


def build_user_mapping_node_lock(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        call_args = inspect.getcallargs(func, *args, **kwargs)
        user = call_args.get('user')
        if user is None or not isinstance(user, User):
            raise ValueError('You function must have `user` argument')

        key = UPDATE_MAPPING_NODE_TASK_LOCK_KEY.format(user_id=user.id)
        doing_value = _generate_value()
        commiting_value = _generate_value(stage=lock.COMMITING)

        try:
            locked = lock.acquire(key, doing_value, timeout=600)
            if not locked:
                logger.error(f'update_mapping_node_task_locked_failed for user: {user.id}')
                raise lock.SomeoneIsDoingThis

            with atomic(savepoint=False):
                func(*args, **kwargs)
                ok = lock.change_lock_state_to_commiting(key, doing_value, commiting_value)
                if not ok:
                    logger.error(f'update_mapping_node_task_timeout for user: {user.id}')
                    raise lock.Timeout
        finally:
            lock.release(key, commiting_value, doing_value)
    return wrapper


@build_user_mapping_node_lock
def rebuild_user_mapping_nodes_if_need_with_lock(user: User):
    tasks = RebuildUserTreeTask.objects.filter(user=user)
    if tasks:
        tasks.delete()
        rebuild_user_mapping_nodes(user)


@build_user_mapping_node_lock
def rebuild_user_mapping_nodes_with_lock(user: User):
    rebuild_user_mapping_nodes(user)


@timeit
def compute_tmp_mapping_node_from_perm(user: User, asset_perms_id=None):
    node_only_fields = ('id', 'key', 'parent_key', 'assets_amount')

    if asset_perms_id is None:
        asset_perms_id = get_user_all_assetpermissions_id(user)

    # 查询直接授权节点
    nodes = Node.objects.filter(
        granted_by_permissions__id__in=asset_perms_id
    ).distinct().only(*node_only_fields)

    # 授权的节点 key 集合
    granted_key_set = {_node.key for _node in nodes}

    def _has_ancestor_granted(node):
        """
        判断一个节点是否有授权过的祖先节点
        """
        ancestor_keys = set(node.get_ancestor_keys())
        return ancestor_keys & granted_key_set

    key2leaf_nodes_mapper = {}

    # 给授权节点设置 _granted 标识，同时去重
    for _node in nodes:
        if _has_ancestor_granted(_node):
            continue

        if _node.key not in key2leaf_nodes_mapper:
            set_granted(_node)
            key2leaf_nodes_mapper[_node.key] = _node

    # 查询授权资产关联的节点设置
    def process_direct_granted_assets():
        # 查询直接授权资产
        asset_ids = Asset.org_objects.filter(
            granted_by_permissions__id__in=asset_perms_id
        ).distinct().values_list('id', flat=True)
        # 查询授权资产关联的节点设置
        granted_asset_nodes = Node.objects.filter(
            assets__id__in=asset_ids
        ).distinct().only(*node_only_fields)

        # 给资产授权关联的节点设置 _asset_granted 标识，同时去重
        for _node in granted_asset_nodes:
            if _has_ancestor_granted(_node):
                continue

            if _node.key not in key2leaf_nodes_mapper:
                key2leaf_nodes_mapper[_node.key] = _node
            set_asset_granted(key2leaf_nodes_mapper[_node.key])

    if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
        process_direct_granted_assets()

    leaf_nodes = key2leaf_nodes_mapper.values()

    # 计算所有祖先节点
    ancestor_keys = set()
    for _node in leaf_nodes:
        ancestor_keys.update(_node.get_ancestor_keys())

    # 从祖先节点 key 中去掉同时也是叶子节点的 key
    ancestor_keys -= key2leaf_nodes_mapper.keys()
    # 查出祖先节点
    ancestors = Node.objects.filter(key__in=ancestor_keys).only(*node_only_fields)
    return [*leaf_nodes, *ancestors]


def create_mapping_nodes(user, nodes):
    to_create = []
    for node in nodes:
        _granted = getattr(node, TMP_GRANTED_FIELD, False)
        _asset_granted = getattr(node, TMP_ASSET_GRANTED_FIELD, False)
        _granted_assets_amount = getattr(node, TMP_GRANTED_ASSETS_AMOUNT_FIELD, 0)
        to_create.append(UserGrantedMappingNode(
            user=user,
            node=node,
            key=node.key,
            parent_key=node.parent_key,
            granted=_granted,
            asset_granted=_asset_granted,
            assets_amount=_granted_assets_amount,
        ))

    UserGrantedMappingNode.objects.bulk_create(to_create)


def set_node_granted_assets_amount(user, node, asset_perms_id=None):
    """
    不依赖`UserGrantedMappingNode`直接查询授权计算资产数量
    """
    _granted = getattr(node, TMP_GRANTED_FIELD, False)
    if _granted:
        assets_amount = node.assets_amount
    else:
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            assets_amount = count_direct_granted_node_assets(user, node.key, asset_perms_id)
        else:
            assets_amount = count_node_all_granted_assets(user, node.key, asset_perms_id)
    setattr(node, TMP_GRANTED_ASSETS_AMOUNT_FIELD, assets_amount)


def compute_node_assets_amount(tmp_nodes: List[Node], asset_perm_ids):
    """
    这里计算的是一个组织的
    """
    if len(tmp_nodes) == 1:
        tmp_node = tmp_nodes[0]
        if is_direct_granted(tmp_node) and tmp_node.key.isdigit():
            # 直接授权了跟节点
            setattr(tmp_node, TMP_GRANTED_ASSETS_AMOUNT_FIELD, tmp_node.assets_amount)
            return

    direct_granted_node_ids = [
        node.id for node in tmp_nodes
        if is_direct_granted(node)
    ]

    # 根据资产授权，取出所有直接授权的资产
    direct_granted_asset_ids = set(
        AssetPermission.assets.through.objects.filter(
            assetpermission_id__in=asset_perm_ids).values_list('asset_id', flat=True)
    )

    # 直接授权资产，取它与它的节点的关系
    node_asset_pairs_1 = Asset.nodes.through.objects.filter(asset_id__in=direct_granted_asset_ids).values_list('node_id', 'asset_id')
    node_asset_pairs_2 = NodeAssetRelatedRecord.objects.filter(node_id__in=direct_granted_node_ids).values_list('node_id', 'asset_id')

    tree = Tree(tmp_nodes, chain(node_asset_pairs_1, node_asset_pairs_2))
    tree.build_tree()
    tree.compute_tree_node_assets_amount()

    for node in tmp_nodes:
        assets_amount = tree.key_tree_node_mapper[node.key].assets_amount
        setattr(node, TMP_GRANTED_ASSETS_AMOUNT_FIELD, assets_amount)


def rebuild_user_mapping_nodes(user, org):
    logger.info(f'>>> {dt_formater(now())} start rebuild {user} mapping nodes')

    with tmp_to_org(org):
        # 先删除旧的授权树🌲
        UserGrantedMappingNode.objects.filter(
            user=user,
            node__org_id=org.id
        ).delete()
        asset_perms_id = get_user_all_assetpermissions_id(user)
        if not asset_perms_id:
            # 没有授权直接返回
            return
        tmp_nodes = compute_tmp_mapping_node_from_perm(user, asset_perms_id=asset_perms_id)
        compute_node_assets_amount(tmp_nodes, asset_perms_id)
        create_mapping_nodes(user, tmp_nodes)
    logger.info(f'>>> {dt_formater(now())} end rebuild {user} mapping nodes')


def get_user_granted_nodes_list_via_mapping_node(user):
    """
    这里的 granted nodes, 是整棵树需要的node，推算出来的也算
    :param user:
    :return:
    """
    # 获取 `UserGrantedMappingNode` 中对应的 `Node`
    nodes = Node.objects.filter(
        mapping_nodes__user=user,
    ).annotate(
        **node_annotate_mapping_node
    ).distinct()

    key_to_node_mapper = {}
    nodes_descendant_q = Q()

    for node in nodes:
        if not is_direct_granted(node):
            # 未授权的节点资产数量设置为 `UserGrantedMappingNode` 中的数量
            node.assets_amount = get_granted_assets_amount(node)
        else:
            # 直接授权的节点
            # 增加查询后代节点的过滤条件
            nodes_descendant_q |= Q(key__startswith=f'{node.key}:')
        key_to_node_mapper[node.key] = node

    if nodes_descendant_q:
        descendant_nodes = Node.objects.filter(
            nodes_descendant_q
        ).annotate(
            **node_annotate_set_granted
        )
        for node in descendant_nodes:
            key_to_node_mapper[node.key] = node

    all_nodes = key_to_node_mapper.values()
    return all_nodes


def get_user_granted_all_assets(
        user, via_mapping_node=True,
        include_direct_granted_assets=True, asset_perms_id=None):
    if asset_perms_id is None:
        asset_perms_id = get_user_all_assetpermissions_id(user)

    if via_mapping_node:
        granted_node_keys = UserGrantedMappingNode.objects.filter(
            user=user, granted=True,
        ).values_list('key', flat=True).distinct()
    else:
        granted_node_keys = Node.objects.filter(
            granted_by_permissions__id__in=asset_perms_id
        ).distinct().values_list('key', flat=True)
    granted_node_keys = Node.clean_children_keys(granted_node_keys)

    granted_node_q = Q()
    for _key in granted_node_keys:
        granted_node_q |= Q(nodes__key__startswith=f'{_key}:')
        granted_node_q |= Q(nodes__key=_key)

    if include_direct_granted_assets:
        assets__id = get_user_direct_granted_assets(user, asset_perms_id).values_list('id', flat=True)
        q = granted_node_q | Q(id__in=list(assets__id))
    else:
        q = granted_node_q

    if q:
        return Asset.org_objects.filter(q).distinct()
    else:
        return Asset.org_objects.none()


def get_node_all_granted_assets(user: User, key):
    """
    此算法依据 `UserGrantedMappingNode` 的数据查询
    1. 查询该节点下的直接授权节点
    2. 查询该节点下授权资产关联的节点
    """

    assets = Asset.objects.none()

    # 查询该节点下的授权节点
    granted_mapping_nodes = UserGrantedMappingNode.objects.filter(
        user=user, granted=True,
    ).filter(
        Q(key__startswith=f'{key}:') | Q(key=key)
    )

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
        asset_perms_id = get_user_all_assetpermissions_id(user)
        only_asset_granted_nodes_q &= Q(granted_by_permissions__id__in=list(asset_perms_id))
        q.append(only_asset_granted_nodes_q)

    if q:
        assets = Asset.objects.filter(reduce(or_, q)).distinct()
    return assets


def get_direct_granted_node_ids(user: User, key, asset_perms_id=None):
    if asset_perms_id is None:
        asset_perms_id = get_user_all_assetpermissions_id(user)

    # 先查出该节点下的直接授权节点
    granted_nodes = Node.objects.filter(
        Q(key__startswith=f'{key}:') | Q(key=key)
    ).filter(
        granted_by_permissions__id__in=asset_perms_id
    ).distinct().only('id', 'key')

    node_ids = set()
    # 根据直接授权节点查询他们的子节点
    q = Q()
    for _node in granted_nodes:
        q |= Q(key__startswith=f'{_node.key}:')
        node_ids.add(_node.id)

    if q:
        descendant_ids = Node.objects.filter(q).values_list('id', flat=True).distinct()
        node_ids.update(descendant_ids)
    return node_ids


def get_node_all_granted_assets_from_perm(user: User, key, asset_perms_id=None):
    """
    此算法依据 `AssetPermission` 的数据查询
    1. 查询该节点下的直接授权节点
    2. 查询该节点下授权资产关联的节点
    """
    if asset_perms_id is None:
        asset_perms_id = get_user_all_assetpermissions_id(user)

    # 直接授权资产查询条件
    q = (
        Q(nodes__key__startswith=f'{key}:') | Q(nodes__key=key)
    ) & Q(granted_by_permissions__id__in=asset_perms_id)

    node_ids = get_direct_granted_node_ids(user, key, asset_perms_id)
    q |= Q(nodes__id__in=node_ids)
    asset_qs = Asset.objects.filter(q).distinct()
    return asset_qs


def get_direct_granted_node_assets_from_perm(user: User, key, asset_perms_id=None):
    node_ids = get_direct_granted_node_ids(user, key, asset_perms_id)
    asset_qs = Asset.objects.filter(nodes__id__in=node_ids).distinct()
    return asset_qs


def count_node_all_granted_assets(user: User, key, asset_perms_id=None):
    return get_node_all_granted_assets_from_perm(user, key, asset_perms_id).count()


def count_direct_granted_node_assets(user: User, key, asset_perms_id=None):
    return get_direct_granted_node_assets_from_perm(user, key, asset_perms_id).count()


def get_indirect_granted_node_children(user, key=''):
    """
    获取用户授权树中未授权节点的子节点
    只匹配在 `UserGrantedMappingNode` 中存在的节点
    """
    nodes = Node.objects.filter(
        mapping_nodes__user=user,
        parent_key=key
    ).annotate(
        _granted_assets_amount=F('mapping_nodes__assets_amount'),
        _granted=F('mapping_nodes__granted')
    ).distinct()

    # 设置节点授权资产数量
    for _node in nodes:
        if not is_direct_granted(_node):
            _node.assets_amount = get_granted_assets_amount(_node)
    return nodes


def get_top_level_granted_nodes(user):
    nodes = list(get_indirect_granted_node_children(user, key=''))
    if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
        ungrouped_node = get_ungrouped_node(user)
        nodes.insert(0, ungrouped_node)
    favorite_node = get_favorite_node(user)
    nodes.insert(0, favorite_node)
    return nodes


def get_user_all_assetpermissions_id(user: User):
    group_ids = user.groups.through.objects.filter(user_id=user.id).distinct().values_list('usergroup_id', flat=True)
    asset_perm_ids = set()
    asset_perm_ids.update(
        AssetPermission.users.through.objects.filter(
            user_id=user.id).distinct().values_list('assetpermission_id', flat=True))
    asset_perm_ids.update(
        AssetPermission.user_groups.through.objects.filter(
            usergroup_id__in=group_ids).distinct().values_list('assetpermission_id', flat=True))
    return asset_perm_ids


def get_user_direct_granted_assets(user, asset_perms_id=None):
    if asset_perms_id is None:
        asset_perms_id = get_user_all_assetpermissions_id(user)
    assets = Asset.org_objects.filter(granted_by_permissions__id__in=asset_perms_id).distinct()
    return assets


def count_user_direct_granted_assets(user, asset_perms_id=None):
    count = get_user_direct_granted_assets(
        user, asset_perms_id=asset_perms_id
    ).values_list('id').count()
    return count


def get_ungrouped_node(user, asset_perms_id=None):
    assets_amount = count_user_direct_granted_assets(user, asset_perms_id)
    return Node(
        id=UNGROUPED_NODE_KEY,
        key=UNGROUPED_NODE_KEY,
        value=UNGROUPED_NODE_VALUE,
        assets_amount=assets_amount
    )


def get_favorite_node(user, asset_perms_id=None):
    assets_amount = FavoriteAsset.get_user_favorite_assets(
        user, asset_perms_id=asset_perms_id
    ).values_list('id').count()
    return Node(
        id=FAVORITE_NODE_KEY,
        key=FAVORITE_NODE_KEY,
        value=FAVORITE_NODE_VALUE,
        assets_amount=assets_amount
    )


def rebuild_user_tree_if_need(request, user):
    """
    升级授权树策略后，用户的数据可能还未初始化，为防止用户显示没有数据
    先检查 MappingNode 如果没有数据，同步创建用户授权树
    """
    if is_true(request.query_params.get('rebuild_tree')) or \
            not UserGrantedMappingNode.objects.filter(user=user).exists():
        try:
            rebuild_user_mapping_nodes_with_lock(user)
        except lock.SomeoneIsDoingThis:
            # 您的数据正在初始化，请稍等
            raise lock.SomeoneIsDoingThis(
                detail=_('Please wait while your data is being initialized'),
                code='rebuild_tree_conflict'
            )
