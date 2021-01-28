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
            nodes = list(Node.objects.all())
            nodes_id = [str(node.id) for node in nodes]
            nodes_assets_id = list(Asset.nodes.through.objects.filter(node__in=nodes_id).values_list('node_id', 'asset_id'))

            node_id_assets_id_mapping = defaultdict(set)
            for node_id, asset_id in nodes_assets_id:
                node_id_assets_id_mapping[str(node_id)].add(str(asset_id))

        t2 = time.time()

        for node in nodes:
            tree_node = self.append_path_to_tree_node(self._root, arg_path=node.key)
            self.set_node_object_to_tree_node(tree_node=tree_node, node=node)
            asset_tree_node_parent = self.append_path_to_tree_node(tree_node, path_key_for_asset)
            for asset_id in node_id_assets_id_mapping[str(node.id)]:
                self.append_path_to_tree_node(tree_node=asset_tree_node_parent, arg_path=asset_id)
                # self.set_asset_object_to_tree_node(tree_node=asset_tree_node, asset=asset)

        t3 = time.time()

        print('t1-t2: {}, t2-t3: {}'.format(t2-t1, t3-t2))
