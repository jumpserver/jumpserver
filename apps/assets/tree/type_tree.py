import time
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from .base import TreeNode
from .asset_tree import AssetGenericTree
from common.utils import lazyproperty, get_logger
from assets.models import Asset
from assets.const import Category, AllTypes
from assets.models import Platform
from django.db.models import Count


logger = get_logger(__file__)

class TypeTreeNode(TreeNode):

    def __init__(self, id, category=None, type=None, _type=None, assets_amount=0, **kwargs):
        super().__init__(**kwargs)
        self.id = id
        self.assets_amount = assets_amount
        self.type = type
        self._type = _type
        self.category = category
    
    @lazyproperty
    def assets_amount_total(self):
        amount = self.assets_amount
        for child in self.children:
            child: TypeTreeNode
            amount += child.assets_amount_total
        return amount


class AssetTypeTree(AssetGenericTree):
    def __init__(self, org=None):
        self.root_key = 'root'
        self.root_name= _('All types')
        super().__init__(org=org)
    
    @lazyproperty
    def platform_id_assets_amount_mapper(self):
        t1 = time.time()
        mapper = self.scope_assets_queryset.values('platform_id').annotate(
            assets_amount=Count('id')
        ).values_list('platform_id', 'assets_amount')
        mapper = {str(pid): assets_amount for pid, assets_amount in mapper}
        t2 = time.time()
        logger.debug(f'AssetTypeTree platform_id_assets_amount_mapper cost time: {t2 - t1}')
        return mapper
    
    def create_tree_nodes(self):
        root = self.create_tree_node(id=self.root_key, key=self.root_key, name=self.root_name)
        tree_nodes = {self.root_key: root}
        platforms = Platform.objects.all().only('id', 'name', 'category', 'type')
        for p in platforms:
            c = p.category
            ck = f'{self.root_key}:category_{c}'
            if ck not in tree_nodes:
                c_name = Category.as_dict().get(p.category, p.category)
                c_node = self.create_tree_node(id=ck, key=ck, name=c_name, category=c, type='category')
                tree_nodes[ck] = c_node
            tk = f'{ck}:type_{p.type}'
            if tk not in tree_nodes:
                t_name = dict(AllTypes.choices()).get(p.type, p.type)
                t_node = self.create_tree_node(id=tk, key=tk, name=t_name, category=c, type='type', _type=p.type)
                tree_nodes[tk] = t_node

            pid = str(p.id)
            pk = f'{tk}:platform_{pid}'
            p_name = p.name
            assets_amount = self.platform_id_assets_amount_mapper.get(pid, 0)
            p_node = self.create_tree_node(id=pid, key=pk, name=p_name, assets_amount=assets_amount, type='platform')
            tree_nodes[pk] = p_node
        return list(tree_nodes.values())


    def create_tree_node(self, id, key, name, assets_amount=0, **kwargs):
        parent_key = ':'.join(key.split(':')[:-1])
        if not parent_key:
            parent_key = None
        return TypeTreeNode(
            id=id,
            key=key,
            name=name,
            assets_amount=assets_amount,
            parent_key=parent_key,
            **kwargs
        )
    
    def _filter_node_assets(self, node_key):
        try:
            pid = int(node_key)
            q = Q(platform_id=pid)
            return self.scope_assets_queryset.filter(q)
        except ValueError:
            pid = None
            return Asset.objects.none()