from collections import defaultdict
from django.db.models import Count, Q

from orgs.utils import current_org
from orgs.models import Organization
from assets.models import Asset, Node, Platform
from assets.const.category import Category
from assets.const.types import AllTypes
from common.utils import get_logger, timeit, lazyproperty

from .tree import TreeNode, Tree

logger = get_logger(__name__)


__all__ = ['AssetTree', 'AssetTreeNode']


class AssetTreeNodeAsset:

    model_values = [
        'id', 'name', 'node_id', 'platform_id', 'address', 
        'is_active', 'comment', 'org_id'
    ]

    def __init__(self, parent_key, **kwargs):
        
        for attr in self.model_values:
            setattr(self, attr, kwargs.get(attr))
        self.parent_key = parent_key

    @lazyproperty
    def org(self):
        return Organization.get_instance(self.org_id)

    @property
    def org_name(self) -> str:
        return self.org.name 


class AssetTreeNode(TreeNode):

    def __init__(self, assets_amount=0, assets_amount_total=0, **kwargs):
        super().__init__(**kwargs)
        self.assets_amount = assets_amount
        self.assets_amount_total = assets_amount_total
        self.assets: list[AssetTreeNodeAsset] = []
    
    def init_assets(self, assets_attrs):
        if not assets_attrs:
            return
        for asset_attrs in assets_attrs:
            asset_attrs['parent_key'] = self.key
            asset = AssetTreeNodeAsset(**asset_attrs)
            self.assets.append(asset)
        return self.assets
    
    def get_assets(self):
        return self.assets
    
    def as_dict(self, simple=True):
        data = super().as_dict(simple=simple)
        data.update({
            'assets_amount_total': self.assets_amount_total,
            'assets_amount': self.assets_amount,
            'assets': len(self.assets),
        })
        return data
    

class AssetTree(Tree):

    TreeNode = AssetTreeNode

    def __init__(self, assets_q_object: Q = None, asset_category=None, asset_type=None, org=None, 
                 with_assets_all=False, with_assets_node_id=None, with_assets_node_levels=None, 
                 with_assets_limit=None, 
                 full_tree=True):
        '''
        :param assets_q_object: 只生成这些资产所在的节点树
        :param category: 只生成该类别资产所在的节点树
        :param org: 只生成该组织下的资产节点树

        :param with_assets_node_id: 仅指定节点下包含资产
        :param with_assets: 所有节点都包含资产
        :param with_assets_limit: 包含资产时, 所有资产的最大数量

        :param full_tree: 完整树包含所有节点，否则只包含节点的资产总数不为0的节点
        '''

        super().__init__()
        ## 通过资产构建节点树, 支持 Q, category, org 等过滤条件 ##
        self._assets_q_object: Q = assets_q_object or Q()
        self._asset_category = self._check_asset_category(asset_category)
        self._asset_type = self._check_asset_type(asset_type)
        self._asset_platform_ids = set()
        self._org: Organization = org or current_org

        # org 下全量节点属性映射, 构建资产树时根据完整的节点进行构建
        self._nodes_attr_mapper  = defaultdict(dict)
        # 节点直接资产数量映射, 用于计算节点下总资产数量
        self._nodes_assets_amount_mapper = defaultdict(int)
        # 节点下是否包含资产
        self._with_assets_node_id = with_assets_node_id # 优先级 1, 指定节点包含资产
        self._with_assets_node_levels = with_assets_node_levels # 优先级 2, 指定节点层级包含资产
        self._with_assets_all = with_assets_all # 优先级 3, 所有节点都包含资产
        self._with_assets_limit = with_assets_limit # 包含资产时, 所有资产的最大数量
        self._node_assets_mapper = defaultdict(dict)

        # 是否包含资产总数量为 0 的节点
        self._full_tree = full_tree

        # 初始化时构建树
        self.build()
    
    def _check_asset_category(self, category):
        if category is None:
            return None
        if category in Category.values:
            return category
        logger.warning(f"Invalid category '{category}' for AssetSearchTree.")
        return None

    def _check_asset_type(self, asset_type):
        if asset_type is None:
            return None
        types = list(dict(AllTypes.choices()).keys())
        if asset_type in types:
            return asset_type
        logger.warning(f"Invalid asset_type '{asset_type}' for AssetSearchTree.")
        return None

    @timeit
    def build(self):
        self._load_nodes_attr_mapper()
        self._load_asset_platforms_if_needed()
        self._load_nodes_assets_amount_mapper()
        self._init_tree()
        self._load_nodes_assets_if_needed()
        self._compute_assets_amount_total()
        self._remove_nodes_with_zero_assets_if_needed()
        self._compute_children_count_total()
    
    @timeit
    def _load_asset_platforms_if_needed(self):
        if self._asset_type:
            q = Q(type=self._asset_type)
        elif self._asset_category:
            q = Q(category=self._asset_category)
        else:
            q = Q()
        ids = ids = Platform.objects.filter(q).values_list('id', flat=True)
        ids = self._uuids_to_string(ids)
        self._asset_platform_ids = set(ids)
    
    @timeit
    def _load_nodes_attr_mapper(self):
        nodes = self._load_nodes_attr()
        for node in list(nodes):
            node['id'] = str(node['id'])
            self._nodes_attr_mapper[node['id']] = node
    
    @timeit
    def _load_nodes_attr(self):
        nodes = Node.objects.filter(org_id=self._org.id).values('id', 'key', 'value')
        nodes = list(nodes)
        return nodes
    
    @timeit
    def _load_nodes_assets_amount_mapper(self):
        q = self._make_assets_q_object()
        nodes_amount = self._load_node_assets_amount(q)
        for nc in list(nodes_amount):
            nid = str(nc['node_id'])
            self._nodes_assets_amount_mapper[nid] = nc['amount']
    
    @timeit
    def _load_node_assets_amount(self, assets_q_object):
        nodes_amount = Asset.objects.filter(assets_q_object).values('node_id').annotate(
            amount=Count('id')
        ).values('node_id', 'amount')
        nodes_amount = list(nodes_amount)
        return nodes_amount
        
    @timeit
    def _make_assets_q_object(self) -> Q:
        q = Q(org_id=self._org.id)
        if self._asset_platform_ids:
            q &= Q(platform_id__in=self._asset_platform_ids) 
        if self._assets_q_object:
            q &= self._assets_q_object
        return q
    
    @timeit
    def _init_tree(self):
        # 保证节点按 key 顺序加载，以便后续构建树时父节点总在子节点前面
        nodes = self._nodes_attr_mapper.values()
        sorted_nodes = sorted(nodes, key=lambda n: [int(i) for i in n['key'].split(':')])
        for node in sorted_nodes:
            nid = node['id']
            data = self._get_tree_node_data(nid)
            node = self.TreeNode(**data)
            self.add_node(node)
    
    def _get_tree_node_data(self, node_id):
        attr = self._nodes_attr_mapper[node_id]
        assets_amount = self._nodes_assets_amount_mapper.get(node_id, 0)
        data = {
            **attr,
            '_id': node_id,
            'key': attr['key'],
            'value': attr['value'],
            'assets_amount': assets_amount,
        }
        return data
    
    @timeit
    def _load_nodes_assets_if_needed(self):
        _need = any([
            self._with_assets_node_id, 
            self._with_assets_node_levels,
            self._with_assets_all, 
        ])
        if not _need:
            return

        q = self._make_assets_q_object()
        if self._with_assets_node_id:
            # 优先级1, 指定节点
            node_ids = [self._with_assets_node_id]
            q &= self._make_assets_q_object_for_node_ids(node_ids)
        elif self._with_assets_node_levels:
            nodes = self.get_nodes(levels=self._with_assets_node_levels)
            node_ids = [ n.id for n in nodes ]
            # 优先级2, 指定层级的节点
            q &= self._make_assets_q_object_for_node_ids(node_ids)
        else:
            # 优先级3, 所有资产
            pass
        
        self._load_nodes_assets_mapper(q)
        self._init_assets_to_nodes()
    
    def _load_nodes_assets_mapper(self, q):
        # 按照 node_key 排序，尽可能保证前面节点的资产较多
        assets = Asset.objects.filter(q).values(*AssetTreeNodeAsset.model_values).order_by('node__key')
        if self._with_assets_limit:
            # 限制资产数量
            assets = assets[:self._with_assets_limit]
        for asset in list(assets):
            nid = asset['node_id'] = str(asset['node_id'])
            aid = asset['id'] = str(asset['id'])
            self._node_assets_mapper[nid][aid] = asset
        
    def _init_assets_to_nodes(self):
        # 将资产初始化到节点树上
        for nid, id_asset_mapper in self._node_assets_mapper.items():
            assets = id_asset_mapper.values()
            if not assets:
                continue
            node = self.get_node_by_id(nid)
            if not node:
                continue
            node: AssetTreeNode
            node.init_assets(list(assets))
    
    def _make_assets_q_object_for_node_ids(self, node_ids) -> Q:
        return Q(node_id__in=node_ids)
        
    @timeit
    def _compute_assets_amount_total(self):
        for node in reversed(list(self.nodes.values())):
            total = node.assets_amount
            for child in node.children:
                child: AssetTreeNode
                total += child.assets_amount_total
            node: AssetTreeNode
            node.assets_amount_total = total

    @timeit
    def _remove_nodes_with_zero_assets_if_needed(self):
        if self._full_tree:
            return
        nodes: list[AssetTreeNode] = list(self.nodes.values())
        nodes_to_remove = [ 
            node for node in nodes if not node.is_root and node.assets_amount_total == 0
        ]
        for node in nodes_to_remove:
            self.remove_node(node)
    
    def get_nodes_by_ids(self, node_ids):
        nodes = []
        for nid in node_ids:
            node = self.get_node_by_id(nid)
            if not node:
                continue
            nodes.append(node)
        return nodes
    
    def get_node_by_id(self, node_id):
        node_attr = self._nodes_attr_mapper[node_id]
        node_key = node_attr.get('key')
        if not node_key:
            return None
        return self.get_node(node_key)
    
    def get_assets(self):
        assets = []
        for node in self.nodes.values():
            node: AssetTreeNode
            _assets = node.get_assets()
            assets.extend(_assets)
        return assets

    def _uuids_to_string(self, uuids):
        return [ str(u) for u in uuids ]
    
    def print(self, count=20, simple=True):
        print('org_name: ', getattr(self._org, 'name', 'No-org'))
        print(f'asset_category: {self._asset_category}')
        super().print(count=count, simple=simple)
