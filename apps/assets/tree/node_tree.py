import os
import time
from django.db import connection
from django.db.models import Q
from .base import Tree, TreeNode
from common.utils import lazyproperty, timeit, get_logger
from orgs.utils import current_org
from common.decorators import Singleton, merge_delay_run
from assets.models import Asset, Node
from collections import defaultdict
from django.core.cache import cache
from .asset_tree import AssetGenericTree

__all__ = ['AssetNodeTree', 'NodeTreeNode']

logger = get_logger(__file__)



@Singleton
class AssetNodeRelation:
    table_name = 'assets_asset_nodes'
    fields = 'node_id, asset_id'
    cache_key_nid_aids_mapper = 'cache_key_node_id_asset_ids_mapper'
    cache_key_nid_aids_mapper_pid = 'cache_key_node_id_asset_ids_mapper_pid'
    pid = os.getpid() 

    def __init__(self):
        self._current_mapper_pid = 0
        self._nid_aids_mapper = defaultdict(set)
        self._nid_aids_mapper = self.load_mapper_from_db()
        self.set_cache_pid(self._current_mapper_pid)
    
    @timeit
    def load_mapper_from_db(self):
        sql = f'SELECT {self.fields} FROM {self.table_name};'
        t1 = time.time()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()   # list[tuple]
        t2 = time.time()
        mapper = defaultdict(set)
        for nid, aid in rows:
            nid = str(nid).replace('-', '')
            aid = str(aid).replace('-', '')
            mapper[nid].add(aid)
        t3 = time.time()
        print('AssetNodeRelation fetch cost time:', t2 - t1, 'init cost time:', t3 - t2)
        return mapper
    
    @property
    def nid_aids_mapper(self):
        self.update_nid_aids_mapper_if_needed()
        return self._nid_aids_mapper
    
    def get_node_assets_ids(self, node_id):
        nid = str(node_id).replace('-', '')
        asset_ids = self.nid_aids_mapper[nid]
        return asset_ids
    
    def update_nid_aids_mapper_if_needed(self):
        pid = self.get_cache_pid()

        # 缓存被清空了
        if pid is None:
            self.refresh_mapper_from_db_to_cache()
            return

        # 没有进程更新数据，使用内存数据
        if pid == self._current_mapper_pid:
            return

        # 有进程更新了数据，加载缓存
        mapper = self.get_cache_mapper()
        if mapper:
            self._current_mapper_pid = pid
            self._nid_aids_mapper = mapper
        else:
            self.refresh_mapper_from_db_to_cache()

    def refresh_mapper_from_db_to_cache(self):
        mapper = self.load_mapper_from_db()
        self.set_cache_mapper(mapper)
        self.set_cache_pid(self.pid)
        self._current_mapper_pid = self.pid
        self._nid_aids_mapper = mapper

    def set_cache_pid(self, pid):
        cache.set(self.cache_key_nid_aids_mapper_pid, pid, None)
    
    def get_cache_pid(self):
        return cache.get(self.cache_key_nid_aids_mapper_pid)

    def set_cache_mapper(self, mapper):
        cache.set(self.cache_key_nid_aids_mapper, mapper, None)
    
    @timeit
    def get_cache_mapper(self):
        return cache.get(self.cache_key_nid_aids_mapper)
    
    def clear_cache(self):
        cache.delete(self.cache_key_nid_aids_mapper)
        cache.delete(self.cache_key_nid_aids_mapper_pid)    


relation = AssetNodeRelation()


class NodeTreeNode(TreeNode):
    def __init__(self, tree, raw_id, **kwargs):
        super().__init__(**kwargs)
        self.tree: AssetNodeTree = tree
        self.id = self.key
        self.raw_id = raw_id
        self.type = 'node'
    
    @lazyproperty
    def assets_ids(self):
        t1 = time.time()
        ids = self.tree.scope_assets_ids & relation.get_node_assets_ids(self.raw_id)
        t2 = time.time()
        if t2 - t1 > 0.3:
            logger.debug(f'NodeTreeNode assets_ids key={self.key} cost time: {t2 - t1}')
        return set(ids)
    
    @property
    def assets_amount(self):
        return len(self.assets_ids)
    
    @lazyproperty
    def assets_ids_total(self):
        ids = set(self.assets_ids)
        for child in self.children:
            child: NodeTreeNode
            ids.update(child.assets_ids_total)
        return ids

    @property
    def assets_amount_total(self):
        return len(self.assets_ids_total)


class AssetNodeTree(AssetGenericTree):

    def __init__(self, category=None, org=None):
        super().__init__(org=org)
        self.category = category
        self.use_cache = False
        self.cache_key_scope_assets_ids = 'cache_key_org_{}_category_{}_scope_assets_ids'.format(
            self.org.id, self.category
        )
        self.cache_key_scope_assets_ids_timeout = 60 * 5  # 5 minutes
    
    @timeit
    def create_tree_nodes(self):
        tree_nodes = []
        nodes = Node.objects.filter(org_id=self.org.id).only('id', 'key', 'value', 'parent_key')
        for node in nodes:
            node_id = str(node.id)
            tree_node = NodeTreeNode(
                tree=self,
                raw_id=node_id,
                key=node.key,
                name=node.value,
                parent_key=node.parent_key or None
            )
            tree_nodes.append(tree_node)
        return tree_nodes
    
    def scope_assets_q(self):
        q = super().scope_assets_q()
        if self.category:
            q &= Q(platform__category=self.category)
        return q

    def set_use_cache(self):
        self.use_cache = True
    
    @lazyproperty
    def scope_assets_ids(self):
        t1 = time.time()
        if self.use_cache:
            cached_assets_ids = cache.get(self.cache_key_scope_assets_ids)
            t2 = time.time()
            if cached_assets_ids:
                logger.debug(f'AssetNodeTree scope_assets_ids cost time cache: {t2 - t1}')
                return cached_assets_ids
        assets_ids = self.scope_assets_queryset.values_list('id', flat=True)
        assets_ids = set([str(i).replace('-', '') for i in assets_ids])
        cache.set(self.cache_key_scope_assets_ids, assets_ids, self.cache_key_scope_assets_ids_timeout)
        t3 = time.time()
        logger.debug(f'AssetNodeTree scope_assets_ids cost time: {t3 - t1}')
        return assets_ids
