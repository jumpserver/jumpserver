# ~*~ coding: utf-8 ~*~
#
from collections import defaultdict
from common.utils import get_logger, dict_get_any, is_uuid, get_object_or_none, timeit
from common.http import is_true
from common.struct import Stack
from common.db.models import output_as_string

from .models import Node

logger = get_logger(__file__)


def is_query_node_all_assets(request):
    request = request
    query_all_arg = request.query_params.get('all', 'true')
    show_current_asset_arg = request.query_params.get('show_current_asset')
    if show_current_asset_arg is not None:
        return not is_true(show_current_asset_arg)
    return is_true(query_all_arg)


def get_node(request):
    node_id = dict_get_any(request.query_params, ['node', 'node_id'])
    if not node_id:
        return None

    if is_uuid(node_id):
        node = get_object_or_none(Node, id=node_id)
    else:
        node = get_object_or_none(Node, key=node_id)
    return node


class NodeAssetsInfo:
    __slots__ = ('key', 'assets_amount', 'assets')

    def __init__(self, key, assets_amount, assets):
        self.key = key
        self.assets_amount = assets_amount
        self.assets = assets

    def __str__(self):
        return self.key


class NodeAssetsUtil:
    def __init__(self, nodes, nodekey_assetsid_mapper):
        """
        :param nodes: 节点
        :param nodekey_assetsid_mapper:  节点直接资产id的映射 {"key1": set(), "key2": set()}
        """
        self.nodes = nodes
        # node_id --> set(asset_id1, asset_id2)
        self.nodekey_assetsid_mapper = nodekey_assetsid_mapper
        self.nodekey_assetsinfo_mapper = {}

    @timeit
    def generate(self):
        # 准备排序好的资产信息数据
        infos = []
        for node in self.nodes:
            assets = self.nodekey_assetsid_mapper.get(node.key, set())
            info = NodeAssetsInfo(key=node.key, assets_amount=0, assets=assets)
            infos.append(info)
        infos = sorted(infos, key=lambda i: [int(i) for i in i.key.split(':')])
        # 这个守卫需要添加一下，避免最后一个无法出栈
        guarder = NodeAssetsInfo(key='', assets_amount=0, assets=set())
        infos.append(guarder)

        stack = Stack()
        for info in infos:
            # 如果栈顶的不是这个节点的父祖节点，那么可以出栈了，可以计算资产数量了
            while stack.top and not info.key.startswith(f'{stack.top.key}:'):
                pop_info = stack.pop()
                pop_info.assets_amount = len(pop_info.assets)
                self.nodekey_assetsinfo_mapper[pop_info.key] = pop_info
                if not stack.top:
                    continue
                stack.top.assets.update(pop_info.assets)
            stack.push(info)

    def get_assets_by_key(self, key):
        info = self.nodekey_assetsinfo_mapper[key]
        return info['assets']

    def get_assets_amount(self, key):
        info = self.nodekey_assetsinfo_mapper[key]
        return info.assets_amount

    @classmethod
    def test_it(cls):
        from assets.models import Node, Asset

        nodes = list(Node.objects.all())
        nodes_assets = Asset.nodes.through.objects.all()\
            .annotate(aid=output_as_string('asset_id'))\
            .values_list('node__key', 'aid')

        mapping = defaultdict(set)
        for key, asset_id in nodes_assets:
            mapping[key].add(asset_id)

        util = cls(nodes, mapping)
        util.generate()
        return util


