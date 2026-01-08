import time
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
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

    def __init__(self, tree, id, category=None, type=None, _type=None, **kwargs):
        super().__init__(**kwargs)
        self.tree = tree
        self.id = id
        self.type = type
        self._type = _type
        self.category = category
    
    @lazyproperty
    def assets_amount(self):
        if self.type != 'platform':
            return 0
        amount = self.tree.platform_id_assets_amount_mapper.get(str(self.id), 0)
        return amount
    
    @lazyproperty
    def assets_amount_total(self):
        amount = self.assets_amount
        for child in self.children:
            child: TypeTreeNode
            amount += child.assets_amount_total
        return amount


class AssetTypeTree(AssetGenericTree):
    def __init__(self, org=None):
        super().__init__(org=org)
        self.root_key = 'root'
        self.root_name= _('All types')
        self.cache_key_platform_assets_amount_mapper = f'''
            cache_key_org_{str(self.org.id)}_platform_assets_amount_mapper 
        '''
        self.cache_key_platform_assets_amount_mapper_timeout = 60 * 5  # 5 minutes
        self.use_cache = False
    
    def set_use_cache(self):
        self.use_cache = True

    @lazyproperty
    def platform_id_assets_amount_mapper(self):
        cache_key = self.cache_key_platform_assets_amount_mapper
        cache_timeout = self.cache_key_platform_assets_amount_mapper_timeout
        t1 = time.time()
        if self.use_cache:
            mapper = cache.get(cache_key)
            if mapper:
                t2 = time.time()
                logger.debug(f'AssetTypeTree platform_id_assets_amount_mapper cache hit cost time: {t2 - t1}')
                return mapper
        mapper = self.scope_assets_queryset.values('platform_id').annotate(
            assets_amount=Count('id')
        ).values_list('platform_id', 'assets_amount')
        mapper = {str(pid): assets_amount for pid, assets_amount in mapper}
        cache.set(cache_key, mapper, cache_timeout)
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
            p_node = self.create_tree_node(id=pid, key=pk, name=p_name, type='platform')
            tree_nodes[pk] = p_node
        return list(tree_nodes.values())

    def create_tree_node(self, id, key, name, **kwargs):
        parent_key = ':'.join(key.split(':')[:-1])
        if not parent_key:
            parent_key = None
        return TypeTreeNode(
            tree=self,
            id=id,
            key=key,
            name=name,
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