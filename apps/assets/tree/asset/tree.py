import time
from collections import defaultdict
from common.utils import timeit
from orgs.utils import tmp_to_org
from assets.models import Asset, Node
from .base import BaseAssetTree


__all__ = ['AssetTree']


class AssetTree(BaseAssetTree):
    """ 资产树 """

    def __init__(self, org_id, **kwargs):
        self._org_id = org_id
        super().__init__(**kwargs)

    @timeit
    def initial(self):
        # TODO: perf 使用线程
        t1 = time.time()
        with tmp_to_org(self._org_id):
            nodes = list(Node.objects.all().values_list('id', 'key'))

            nodes_id = [str(node_id) for node_id, node_key in nodes]
            nodes_assets_id = Asset.nodes.through.objects.filter(node_id__in=nodes_id).values_list(
                'node_id', 'asset_id'
            )
            nodes_assets_id_mapping = defaultdict(set)
            for node_id, asset_id in nodes_assets_id:
                nodes_assets_id_mapping[str(node_id)].add(str(asset_id))

        t2 = time.time()

        for node_id, node_key in nodes:
            tree_node = self.append_path_to_tree_node(self._root, arg_path=node_key)
            tee_node_of_asset = self.append_path_to_tree_node(tree_node, self._flag_for_asset)
            for asset_id in nodes_assets_id_mapping[str(node_id)]:
                self.append_path_to_tree_node(tee_node_of_asset, arg_path=asset_id)

        t3 = time.time()

        print('t1-t2: {}, t2-t3: {}'.format(t2-t1, t3-t2))


