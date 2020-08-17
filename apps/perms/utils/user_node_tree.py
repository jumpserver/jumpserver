from itertools import chain

from django.db.models import F, Count, Value, BooleanField

from assets.models import Node, Asset
from perms.models import GrantedNode
from users.models import User


def inc_granted_count(obj, value=1):
    obj._granted_count = getattr(obj, '_granted_count', 0) + value


def inc_asset_granted_count(obj, value=1):
    obj._asset_granted_count = getattr(obj, '_asset_granted_count', 0) + value


ADD = 'add'
REMOVE = 'remove'


def update_users_tree_for_add(users,
                              nodes=(),
                              assets=(),
                              action=ADD):
    """
    `_granted_count` 授权次数，等于节点数或者资产数
    """

    # 查询授权`Asset`关联的 `Node`
    asset_granted_nodes_qs = Node.objects.filter(
        assets__in=assets
    ).annotate(
        _granted_count=Count('assets', distinct=True),
        _asset_granted_count=Count('assets', distinct=True),
    ).distinct()

    asset_granted_nodes = []
    for n in asset_granted_nodes_qs:
        n._granted = False
        asset_granted_nodes.append(n)

    # 授权的 `Node`
    for n in nodes:
        inc_granted_count(n)
        n._granted = True
    # 资产授权节点与直接授权节点总共的祖先`key`，因为两者可能会重叠，所以字典的键复杂
    ancestor_keys_map = {(n, n._granted): n.get_ancestor_keys() for n in chain(asset_granted_nodes, nodes)}
    ancestors_map = {node.key: node for node in
                     Node.objects.filter(key__in=chain(*ancestor_keys_map.values()))}
    for (node, _), keys in ancestor_keys_map.items():
        for key in keys:
            ancestor = ancestors_map[key]  # TODO 404
            inc_granted_count(ancestor, node._granted_count)
    keys = ancestors_map.keys() | {n.key for n, _ in ancestor_keys_map.keys()}
    # 资产授权节点和直接授权节点，两者会有重叠
    all_nodes = [*nodes, *asset_granted_nodes, *ancestors_map.values()]

    for user in users:
        # 每个用户单独处理自己的树
        to_create = {}
        to_update = []
        _granted_nodes = GrantedNode.objects.filter(key__in=keys, user=user)
        granted_nodes_map = {gn.key: gn for gn in _granted_nodes}
        for node in all_nodes:
            _granted = getattr(node, '_granted', False)
            _asset_granted_count = getattr(node, '_asset_granted_count', 0)
            _granted_count = getattr(node, '_granted_count')
            if node.key in granted_nodes_map:
                granted_node = granted_nodes_map[node.key]
                if action == ADD:
                    if _granted:
                        if granted_node.granted:
                            #相同节点不能授权两次
                            raise ValueError('')
                        granted_node.granted = True

                    inc_asset_granted_count(granted_node, _asset_granted_count)
                    inc_granted_count(granted_node, _granted_count)
                elif action == REMOVE:
                    if _granted:
                        if not granted_node.granted:
                            # 数据有问题
                            raise ValueError('')
                        granted_node.granted = False
                    inc_asset_granted_count(granted_node, -_asset_granted_count)
                    inc_granted_count(granted_node, -_granted_count)

                to_update.append(granted_node)
            else:
                if action == REMOVE:
                    # 数据有问题
                    raise ValueError('')
                if node.key not in to_create:
                    granted_node = GrantedNode(
                        key=node.key,
                        user=user,
                        granted=_granted,
                        granted_count=_granted_count,
                        asset_granted_count=_asset_granted_count
                    )
                    to_create[node.key] = granted_node
                else:
                    granted_node = to_create[node.key]
                    granted_node.granted_count += _granted_count
                    granted_node.asset_granted_count += _asset_granted_count
                    if _granted:
                        if granted_node.granted:
                            raise ValueError()
                        granted_node.granted = True

        for gn in to_update:
            gn.granted_count = F('granted_count') + gn._granted_count
            gn.asset_granted_count = F('asset_granted_count') + getattr(gn, '_asset_granted_count', 0)
        GrantedNode.objects.bulk_update(to_update, ('granted', 'granted_count', 'asset_granted_count'))
        GrantedNode.objects.bulk_create(to_create.values())
