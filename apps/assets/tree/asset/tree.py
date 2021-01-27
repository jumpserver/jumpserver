import time
from collections import defaultdict
from common.utils import timeit
from orgs.utils import tmp_to_org
from assets.models import Asset, Node
from .base import BaseAssetTree, path_key_for_asset


__all__ = ['AssetTree']


class AssetTree(BaseAssetTree):
    """ 资产树 """

    def __init__(self, org_id, **kwargs):
        self._org_id = org_id
        super().__init__(**kwargs)

    @timeit
    def initial(self):
        t1 = time.time()

        with tmp_to_org(self._org_id):
            nodes_id_key = list(Node.objects.all().values_list('id', 'key'))
            nodes_id = [str(node_id) for node_id, node_key in nodes_id_key]
            nodes_assets_id = Asset.nodes.through.objects\
                .filter(node_id__in=nodes_id)\
                .values_list('node_id', 'asset_id')

            nodes_assets_id_mapping = defaultdict(set)
            for node_id, asset_id in nodes_assets_id:
                nodes_assets_id_mapping[str(node_id)].add(str(asset_id))

        t2 = time.time()

        for node_id, node_key in nodes_id_key:
            tree_node = self.append_path_to_tree_node(self._root, arg_path=node_key)
            asset_tree_node_parent = self.append_path_to_tree_node(tree_node, path_key_for_asset)
            for _asset_id in nodes_assets_id_mapping[str(node_id)]:
                self.append_path_to_tree_node(asset_tree_node_parent, arg_path=_asset_id)

        t3 = time.time()

        print('t1-t2: {}, t2-t3: {}'.format(t2-t1, t3-t2))
