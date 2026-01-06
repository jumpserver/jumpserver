from collections import defaultdict
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q

from assets.api import node

# 类别视图的资产树
from .tree import Tree, TreeNode
from .node_tree import AssetTree, AssetTreeNode, AssetTreeNodeAsset
from assets.models import Platform, Asset
from common.utils import timeit, get_logger


__all__ = ['AssetTreeCategoryView']

logger = get_logger(__name__)


class AssetTreeNodeCategoryView(AssetTreeNode):

    class Type:
        ROOT = 'root'
        CATEGORY = 'category'
        TYPE = 'type'
        PLATFORM = 'platform'

    def __init__(self, type_, raw_id=None, **kwargs):
        super().__init__(**kwargs)
        self._type = type_
        self._raw_id = raw_id
    
    @property
    def is_platform(self):
        return self._is_type(self.Type.PLATFORM)
    
    def _is_type(self, tp):
        return self._type == tp


class AssetTreeCategoryView(AssetTree):

    TreeNode = AssetTreeNodeCategoryView

    def __init__(self, **kwargs):
        self.__root_key = '1'
        self.__root_id = self.__root_key
        self.__root_value = _('All Categories')
        self._platforms_attr_mapper = {}
        super().__init__(**kwargs)
    
    def build(self):
        self._load_platforms_attr_mapper()
        super().build()
    
    def _load_platforms_attr_mapper(self):
        platforms = Platform.objects.all().values('id', 'name', 'category', 'type')
        for platform in platforms:
            pid = str(platform['id'])
            self._platforms_attr_mapper[pid] = platform

    @timeit
    def _load_nodes_attr(self):
        nodes_attr = []
        root = { 
            'id': self.__root_id, 'key': self.__root_key, 'value': self.__root_value,
            'type_': AssetTreeNodeCategoryView.Type.ROOT
        }
        nodes_attr.append(root)

        platforms = Platform.objects.values('category', 'type', 'name', 'id').order_by(
            'category', 'type', 'name'
        )
        platforms = list(platforms)
        nested_category_type_platform_mapper = defaultdict(lambda: defaultdict(dict))
        for platforms in platforms:
            c_name = platforms['category']
            t_name = platforms['type']
            pid = str(platforms['id'])
            p_name = platforms['name']
            nested_category_type_platform_mapper[c_name][t_name][pid] = p_name
        
        for _ck, (c_name, types) in enumerate(nested_category_type_platform_mapper.items(), start=1):
            ck = f'{self.__root_key}:{_ck}'
            cid = ck
            ctype = AssetTreeNodeCategoryView.Type.CATEGORY
            category_node = { 'id': cid, 'key': ck, 'value': c_name, 'type_': ctype }
            nodes_attr.append(category_node)
            for _tk, (t_name, platforms) in enumerate(types.items(), start=1):
                tk = f'{ck}:{_tk}'
                tid = tk
                ttype = AssetTreeNodeCategoryView.Type.TYPE
                type_node = { 'id': tid, 'key': tk, 'value': t_name, 'type_': ttype }
                nodes_attr.append(type_node)
                for _pk, (pid, p_name) in enumerate(platforms.items(), start=1):
                    pk = f'{tk}:{_pk}'
                    _pid = pk
                    ptype = AssetTreeNodeCategoryView.Type.PLATFORM
                    platform_node = { 
                        'id': _pid, 'key': pk, 'value': p_name, 'type_': ptype, 'raw_id': pid 
                    }
                    nodes_attr.append(platform_node)
        return nodes_attr
    
    def _load_node_assets_amount(self, assets_q_object):
        platforms_amount = Asset.objects.filter(assets_q_object).values('platform_id').annotate(
            amount=Count('id'),
        ).values('platform_id', 'amount')
        nodes_amount = []
        for platform in platforms_amount:
            pid = platform['platform_id']
            amount = platform['amount']
            node_id = self._get_platform_tree_node_id(platform_id=pid)
            nodes_amount.append({ 'node_id': node_id, 'amount': amount })
        return nodes_amount
    
    def _make_assets_q_object_for_node_ids(self, node_ids) -> Q:
        nodes = self.get_nodes_by_ids(node_ids)
        platform_ids = set()
        for n in nodes:
            n: AssetTreeNodeCategoryView
            if not n.is_platform:
                continue
            if not n._raw_id:
                continue
            platform_ids.add(int(n._raw_id))
        return Q(platform_id__in=platform_ids)
    
    def _load_nodes_assets_mapper(self, q):
        # 按照 node_key 排序，尽可能保证前面节点的资产较多
        # order_by 和构造节点时保持一致
        assets = Asset.objects.filter(q).values(*AssetTreeNodeAsset.model_values).order_by(
            'platform__category', 'platform__type', 'platform__name'
        )
        if self._with_assets_limit:
            # 限制资产数量
            assets = assets[:self._with_assets_limit]
        for asset in list(assets):
            platform_id = str(asset['platform_id'])
            tn_id =  self._get_platform_tree_node_id(platform_id)
            aid = asset['id'] = str(asset['id'])
            asset['node_id'] = str(asset['node_id'])
            self._node_assets_mapper[tn_id][aid] = asset
    
    def _get_platform_tree_node_id(self, platform_id):
        platforms = [
            n for n in self._nodes_attr_mapper.values() 
            if (
                n['type_'] == AssetTreeNodeCategoryView.Type.PLATFORM and 
                n.get('raw_id') == str(platform_id)
            )
        ]
        if not platforms:
            logger.warning(f"Platform with ID {platform_id} not found in attribute mapper.")
            return
        return platforms[0].get('id')
