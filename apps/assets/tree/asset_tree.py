from collections import defaultdict
from django.db.models import Count, Q

from orgs.utils import current_org
from orgs.models import Organization
from assets.models import Asset, Node, Platform
from assets.const.category import Category
from common.utils import get_logger, timeit

from .tree import TreeNode, Tree

logger = get_logger(__name__)


__all__ = ['AssetTree', 'AssetTreeNode']


class AssetTreeNode(TreeNode):

    def __init__(self, _id, key, value, assets_count=0, assets=None):
        super().__init__(_id, key, value)
        self.assets_count = assets_count
        self.assets_count_total = 0
        self.assets = assets or set()
    
    def as_dict(self, simple=True):
        data = super().as_dict(simple=simple)
        data.update({
            'assets_count_total': self.assets_count_total,
            'assets_count': self.assets_count,
            'assets': len(self.assets),
        })
        return data
    

class AssetTree(Tree):

    TreeNode = AssetTreeNode

    def __init__(self, assets_q_object: Q = None, category=None, org=None, 
                 with_assets=False, full_tree=False):

        super().__init__()
        self._org: Organization = org or current_org()
        self._nodes_attr_mapper  = defaultdict(dict)
        self._nodes_assets_count_mapper = defaultdict(int)
        # 过滤资产的 Q 对象
        self._q_assets: Q = assets_q_object or Q()
        # 通过类别过滤资产
        self._category = self._check_category(category)
        self._category_platform_ids = set()
        # 节点下是否包含资产
        self._with_assets = with_assets
        self._node_assets_mapper = defaultdict(dict)
        # 是否构建完整树，包含所有节点，否则只包含有资产的节点
        self._full_tree = full_tree
    
    def _check_category(self, category):
        if category is None:
            return None
        if category in Category.values:
            return category
        logger.warning(f"Invalid category '{category}' for AssetSearchTree.")
        return None

    @timeit
    def build(self):
        self._load_nodes_attr_mapper()
        self._load_category_platforms_if_needed()

        if self._with_assets:
            self._load_nodes_assets_and_count()
        else:
            self._load_nodes_assets_count()

        self._init_tree()
        self._compute_assets_count_total()
        self._remove_nodes_with_zero_assets_if_needed()
    
    @timeit
    def _load_category_platforms_if_needed(self):
        if self._category is None:
            return
        ids = Platform.objects.filter(category=self._category).values_list('id', flat=True)
        ids = self._uuids_to_string(ids)
        self._category_platform_ids = ids

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
        q = self._make_assets_q_object()
        nodes_count = Asset.objects.filter(q).values('node_id').annotate(
            count=Count('id')
        ).values('node_id', 'count')
        for nc in list(nodes_count):
            nid = str(nc['node_id'])
            self._nodes_assets_count_mapper[nid] = nc['count']
    
    @timeit
    def _load_nodes_assets_and_count(self):
        q = self._make_assets_q_object()
        assets = Asset.objects.filter(q).values(
            'node_id', 'id', 'platform_id', 'name', 'address', 'is_active', 'comment', 'org_id'
        )
        for asset in list(assets):
            asset['id'] = str(asset['id'])
            asset['platform_id'] = str(asset['platform_id'])
            asset['node_id'] = str(asset['node_id'])
            nid = str(asset['node_id'])
            aid = str(asset['id'])
            self._node_assets_mapper[nid][aid] = asset
        
        for nid, assets in self._node_assets_mapper.items():
            self._nodes_assets_count_mapper[nid] = len(assets)
    
    @timeit
    def _make_assets_q_object(self) -> Q:
        q = Q(org_id=self._org.id)
        if self._category_platform_ids:
            q &= Q(platform_id__in=self._category_platform_ids) 
        if self._q_assets:
            q &= self._q_assets
        return q
    
    @timeit
    def _init_tree(self):
        for nid in self._nodes_attr_mapper.keys():
            data = self._get_tree_node_data(nid)
            node = self.TreeNode(**data)
            self.add_node(node)
    
    def _get_tree_node_data(self, node_id):
        attr = self._nodes_attr_mapper[node_id]
        assets_count = self._nodes_assets_count_mapper.get(node_id, 0)
        data = {
            '_id': node_id,
            'key': attr['key'],
            'value': attr['value'],
            'assets_count': assets_count,
        }
        if self._with_assets:
            assets = self._node_assets_mapper.get(node_id, set())
            data.update({ 'assets': assets })
        return data
    
    @timeit
    def _compute_assets_count_total(self):
        for node in reversed(list(self.nodes.values())):
            total = node.assets_count
            for child in node.children:
                child: AssetTreeNode
                total += child.assets_count_total
            node: AssetTreeNode
            node.assets_count_total = total
    @timeit
    def _remove_nodes_with_zero_assets_if_needed(self):
        if self._full_tree:
            return
        nodes: list[AssetTreeNode] = list(self.nodes.values())
        nodes_to_remove = [ 
            node for node in nodes if not node.is_root and node.assets_count_total == 0
        ]
        for node in nodes_to_remove:
            self.remove_node(node)

    def _uuids_to_string(self, uuids):
        return [ str(u) for u in uuids ]
    
    def print(self, count=20, simple=True):
        print('org_name: ', getattr(self._org, 'name', 'No-org'))
        print(f'asset_category: {self._category}')
        super().print(count=count, simple=simple)
