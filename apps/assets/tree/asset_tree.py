from orgs.utils import current_org
from django.db.models import Q
from assets.models import Asset, Node
from common.utils import timeit, lazyproperty

from .base import Tree

__all__ = ['AssetGenericTree']

class AssetGenericTree(Tree):

    def __init__(self, org):
        self.org = org or current_org
        super().__init__()
    
    @timeit
    def init(self):
        tree_nodes = self.create_tree_nodes()
        super().init(tree_nodes)
    
    @timeit
    def create_tree_nodes(self):
        raise NotImplementedError()
    
    def scope_assets_q(self):
        return Q(org_id=self.org.id)
    
    @lazyproperty
    def scope_assets_queryset(self):
        q = self.scope_assets_q()
        return Asset.objects.filter(q)

    def filter_assets(self, node_key=None, keyword=None):
        only_fields = ['id', 'name', 'address', 'platform_id', 'org_id', 'is_active', 'comment']
        if keyword:
            limit = 1000
            q = Q(name__icontains=keyword) | Q(address__icontains=keyword)
            assets = self.scope_assets_queryset.filter(q)[:limit]
        elif node_key:
            assets = self._filter_node_assets(node_key)
        else:
            assets = self.scope_assets_queryset
        assets = assets.only(*only_fields)
        return assets
    
    def _filter_node_assets(self, node_key):
        q = Q(nodes__key=node_key)
        assets = self.scope_assets_queryset.filter(q)
        return assets