import time
import os
from collections import defaultdict
from common.utils import timeit
from orgs.utils import tmp_to_org
from assets.models import Asset, Node
from .base import BaseAssetTree, path_key_for_asset
from django.db.models import CharField, ExpressionWrapper, F


__all__ = ['AssetTree']


class AssetTree(BaseAssetTree):
    """ 资产树 """

    def __init__(self, org_id, **kwargs):
        """
        * 重要:
        *     节省大量内存, 字符串驻留机制不允许有`-`等特殊字符
        *     解决内存占用问题 (组织下所有资产id从数据库查询出来后首先从这个地方获取内存中资产id的字符串对象)
        * 参考:
        *     https://zhuanlan.zhihu.com/p/35362912
        """
        self._assets_id_dict = {}

        self._org_id = org_id
        super().__init__(**kwargs)

    @timeit
    def initial(self):
        print(os.getpid())
        t1 = time.time()

        with tmp_to_org(self._org_id):
            # * Important
            self.initial_assets_id_to_memory()

            nodes = dict(
                Node.objects.all().annotate(id_of_char=self.expression_wrapper_of_char_field('id'))
                    .values_list('id_of_char', 'key')
            )
            nodes_id = list(nodes.keys())
            nodes_assets_id = list(
                (node_id, self.get_asset_id_from_memory(asset_id))
                for node_id, asset_id in
                Asset.nodes.through.objects.filter(node__in=nodes_id).annotate(
                    node_id_of_char=self.expression_wrapper_of_char_field('node_id'),
                    asset_id_of_char=self.expression_wrapper_of_char_field('asset_id')
                ).values_list('node_id_of_char', 'asset_id_of_char')
            )
            t2 = time.time()

        node_id_assets_id_mapping = defaultdict(set)
        for node_id, asset_id in nodes_assets_id:
            node_id_assets_id_mapping[node_id].add(asset_id)

        for node_id, node_key in nodes.items():
            tree_node = self.append_path_to_tree_node(self._root, arg_path=node_key)
            asset_tree_node_parent = self.append_path_to_tree_node(tree_node, path_key_for_asset)
            for asset_id in node_id_assets_id_mapping[str(node_id)]:
                self.append_path_to_tree_node(tree_node=asset_tree_node_parent, arg_path=asset_id)

        t3 = time.time()

        print('t1-t2: {}, t2-t3: {}'.format(t2-t1, t3-t2))

    def initial_assets_id_to_memory(self):
        """ * Important """
        if self._assets_id_dict:
            return
        assets_id = Asset.objects.filter() \
            .annotate(id_of_char=ExpressionWrapper(F('id'), output_field=CharField())) \
            .values_list('id_of_char', flat=True)
        self._assets_id_dict = {asset_id: asset_id for asset_id in assets_id}

    def get_asset_id_from_memory(self, asset_id):
        """ * Important """
        return self._assets_id_dict[asset_id]

    @staticmethod
    def expression_wrapper_of_char_field(filed_name):
        return ExpressionWrapper(F(filed_name), output_field=CharField())
