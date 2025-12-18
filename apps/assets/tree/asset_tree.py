from collections import defaultdict
from django.db.models import Count

from orgs.utils import current_org
from assets.models import Asset, Node
from common.utils import get_logger, timeit

from .tree import TreeNode, Tree

logger = get_logger(__name__)


__all__ = ['AssetTree']


class AssetTreeNode(TreeNode):

    def __init__(self, _id, key: str, value: str, assets_count: int=0):
        super().__init__(_id, key, value)
        self.assets_count = assets_count
        self.assets_count_total = 0
    
    def as_dict(self, simple=True):
        base_dict = super().as_dict(simple=simple)
        base_dict.update({
            'assets_count_total': self.assets_count_total,
        })
        if not simple:
            base_dict.update({
                'assets_count': self.assets_count,
            })
        return base_dict
    

class AssetTree(Tree):

    def __init__(self, org=None):
        super().__init__()
        self._org = org or current_org()
        self._nodes_attr_mapper  = defaultdict(dict)
        self._nodes_assets_count_mapper = defaultdict(int)

    @timeit
    def build(self):
        self._load_nodes_attr_mapper()
        self._load_nodes_assets_count()
        self._init_tree()
        self._compute_assets_count_total()

    @timeit
    def _load_nodes_attr_mapper(self):
        nodes = Node.objects.filter(org_id=self._org.id).values('id', 'key', 'value')
        # 保证节点按 key 顺序加载，以便后续构建树时父节点总在子节点前面
        nodes = sorted(nodes, key=lambda n: [int(i) for i in n['key'].split(':')])
        for node in list(nodes):
            node['id'] = str(node['id'])
            self._nodes_attr_mapper[node['id']] = node
    
    @timeit
    def _load_nodes_assets_count(self):
        nodes_count = Asset.objects.filter(org_id=self._org.id).values('node_id').annotate(
            count=Count('id')
        ).values('node_id', 'count')
        for nc in list(nodes_count):
            nc['node_id'] = str(nc['node_id'])
            self._nodes_assets_count_mapper[nc['node_id']] = nc['count']
    
    @timeit
    def _init_tree(self):
        for nid, attr in self._nodes_attr_mapper.items():
            assets_count = self._nodes_assets_count_mapper.get(nid, 0)
            node = AssetTreeNode(
                _id=nid,
                key=attr['key'],
                value=attr['value'],
                assets_count=assets_count
            )
            self.add_node(node)

    @timeit
    def _compute_assets_count_total(self):
        for node in reversed(list(self.nodes.values())):
            total = node.assets_count
            for child in node.children:
                child: AssetTreeNode
                total += child.assets_count_total
            node: AssetTreeNode
            node.assets_count_total = total
