from collections import defaultdict
from django.db.models import Count, Q

from orgs.utils import current_org
from orgs.models import Organization
from assets.models import Asset, Node, Platform
from assets.const.category import Category
from common.utils import get_logger, timeit

from .tree import TreeNode, Tree

logger = get_logger(__name__)


__all__ = ['AssetTree', 'AssetSearchTree']


class AssetTreeNode(TreeNode):

    def __init__(self, _id, key: str, value: str, assets_count: int=0):
        super().__init__(_id, key, value)
        self.assets_count = assets_count
        self.assets_count_total = 0
    
    def as_dict(self, simple=True):
        base_dict = super().as_dict(simple=simple)
        base_dict.update({
            'assets_count_total': self.assets_count_total,
            'assets_count': self.assets_count,
        })
        return base_dict
    

class AssetTree(Tree):

    TreeNode = AssetTreeNode

    def __init__(self, org=None):
        super().__init__()
        self._org: Organization = org or current_org()
        self._nodes_attr_mapper  = defaultdict(dict)
        self._nodes_assets_count_mapper = defaultdict(int)

    @timeit
    def build(self):
        self._pre_build()
        self._load_nodes_attr_mapper()
        self._load_nodes_assets_count()
        self._init_tree()
        self._compute_assets_count_total()
        self._after_build()
    
    def _pre_build(self):
        """ 预处理操作 """
        pass

    def _after_build(self):
        """ 构建完成后的操作 """
        pass

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
        q_ = self._make_assets_q_object()
        nodes_count = Asset.objects.filter(q_).values('node_id').annotate(
            count=Count('id')
        ).values('node_id', 'count')
        for nc in list(nodes_count):
            nc['node_id'] = str(nc['node_id'])
            self._nodes_assets_count_mapper[nc['node_id']] = nc['count']
    
    @timeit
    def _make_assets_q_object(self) -> Q:
        q_org = Q(org_id=self._org.id)
        return q_org
    
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



class AssetSearchTree(AssetTree):

    def __init__(self, assets_q_object: Q = None, category=None, org=None):
        super().__init__(org)
        self._q_assets: Q = assets_q_object or Q()
        self._category = self._check_category(category)
        self._platform_ids = set()
    
    def _check_category(self, category):
        if category is None:
            return None
        if category in Category.values:
            return category
        logger.warning(f"Invalid category '{category}' for AssetSearchTree.")
        return None

    def _after_build(self):
        super()._after_build()
        # 搜索树一般需要移除掉资产数为 0 的节点，只保留有资产的节点
        self._remove_nodes_with_zero_assets()
    
    def _make_assets_q_object(self) -> Q:
        q_org = super()._make_assets_q_object()
        self._load_category_platforms_if_needed()
        q_platform = Q(platform_id__in=self._platform_ids) if self._platform_ids else Q()
        q = q_org & q_platform & self._q_assets
        return q
    
    @timeit
    def _load_category_platforms_if_needed(self):
        if self._category is None:
            return
        ids = Platform.objects.filter(category=self._category).values_list('id', flat=True)
        ids = self._uuids_to_string(ids)
        self._platform_ids = ids
    
    @timeit
    def _remove_nodes_with_zero_assets(self):
        nodes: list[AssetTreeNode] = list(self.nodes.values())
        nodes_to_remove = [ 
            node for node in nodes 
            # 不移除根节点
            if not node.is_root and node.assets_count_total == 0
        ]
        for node in nodes_to_remove:
            self.remove_node(node)
    
    def _uuids_to_string(self, uuids):
        return [ str(u) for u in uuids ]