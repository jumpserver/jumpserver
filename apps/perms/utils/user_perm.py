from django.conf import settings
from django.db.models import Q

from assets.models import FavoriteAsset, Asset
from common.utils.common import timeit, lazyproperty
from perms.models import PermNode, UserAssetGrantedTreeNodeRelation
from .permission import AssetPermissionUtil

__all__ = ['AssetPermissionPermAssetUtil', 'UserPermAssetUtil', 'UserPermNodeUtil']


class AssetPermissionPermAssetUtil:

    def __init__(self, perm_ids):
        self.perm_ids = perm_ids

    @lazyproperty
    def all_permed_assets_ids(self):
        node_asset_ids = self.get_perm_nodes_assets(flat=True)
        direct_asset_ids = self.get_direct_assets(flat=True)
        asset_ids = list(node_asset_ids) + list(direct_asset_ids)
        return [str(i) for i in asset_ids]

    def get_all_assets(self):
        """ 获取所有授权的资产 """
        assets = Asset.objects.filter(id__in=self.all_permed_assets_ids)
        return assets

    def get_perm_nodes_assets(self, flat=False):
        """ 获取所有授权节点下的资产 """
        from assets.models import Node
        nodes = Node.objects.prefetch_related('granted_by_permissions').filter(
            granted_by_permissions__in=self.perm_ids).only('id', 'key')
        assets = PermNode.get_nodes_all_assets(*nodes)
        if flat:
            return assets.values_list('id', flat=True)
        return assets

    def get_direct_assets(self, flat=False):
        """ 获取直接授权的资产 """
        assets = Asset.objects.order_by() \
            .filter(granted_by_permissions__id__in=self.perm_ids) \
            .distinct()
        if flat:
            return assets.values_list('id', flat=True)
        return assets


class UserPermAssetUtil(AssetPermissionPermAssetUtil):

    def __init__(self, user):
        self.user = user
        perm_ids = AssetPermissionUtil().get_permissions_for_user(self.user, flat=True)
        super().__init__(perm_ids)

    def get_ungroup_assets(self):
        return self.get_direct_assets()

    def get_favorite_assets(self):
        assets = self.get_all_assets()
        asset_ids = FavoriteAsset.objects.filter(user=self.user).values_list('asset_id', flat=True)
        assets = assets.filter(id__in=list(asset_ids))
        return assets

    def get_node_assets(self, key):
        node = PermNode.objects.get(key=key)
        node.compute_node_from_and_assets_amount(self.user)
        if node.node_from == node.NodeFrom.granted:
            assets = Asset.objects.filter(nodes__id=node.id).order_by()
        elif node.node_from == node.NodeFrom.asset:
            assets = self._get_indirect_perm_node_assets(node)
        else:
            assets = Asset.objects.none()
        assets = assets.order_by('name')
        return assets

    def get_node_all_assets(self, node_id):
        """ 获取节点下的所有资产 """
        node = PermNode.objects.get(id=node_id)
        node.compute_node_from_and_assets_amount(self.user)
        if node.node_from == node.NodeFrom.granted:
            assets = PermNode.get_nodes_all_assets(node)
        elif node.node_from in (node.NodeFrom.asset, node.NodeFrom.child):
            node.assets_amount = node.granted_assets_amount
            assets = self._get_indirect_perm_node_all_assets(node)
        else:
            node.assets_amount = 0
            assets = Asset.objects.none()
        return node, assets

    def _get_indirect_perm_node_assets(self, node):
        """ 获取间接授权节点下的直接资产 """
        assets = self.get_direct_assets()
        assets = assets.filter(nodes__id=node.id).order_by().distinct()
        return assets

    def _get_indirect_perm_node_all_assets(self, node):
        """  获取间接授权节点下的所有资产
        此算法依据 `UserAssetGrantedTreeNodeRelation` 的数据查询
            1. 查询该节点下的直接授权节点
            2. 查询该节点下授权资产关联的节点
        """
        # 查询节点下直接授权的子节点
        asset_ids = set()
        children_from_granted = UserAssetGrantedTreeNodeRelation.objects \
            .filter(user=self.user) \
            .filter(node_key__startswith=f'{node.key}:', node_from=node.NodeFrom.granted) \
            .only('node_id', 'node_key')
        for n in children_from_granted:
            n.id = n.node_id
        _assets = PermNode.get_nodes_all_assets(*children_from_granted)
        _asset_ids = _assets.values_list('id', flat=True)
        asset_ids.update(list(_asset_ids))

        # 查询节点下资产授权的节点
        children_from_assets = UserAssetGrantedTreeNodeRelation.objects \
            .filter(user=self.user) \
            .filter(node_key__startswith=f'{node.key}:', node_from=node.NodeFrom.asset) \
            .values_list('node_id', flat=True)
        children_from_assets = set(children_from_assets)
        if node.node_from == node.NodeFrom.asset:
            children_from_assets.add(node.id)
        _asset_ids = Asset.objects \
            .filter(nodes__id__in=children_from_assets) \
            .filter(granted_by_permissions__id__in=self.perm_ids) \
            .distinct() \
            .order_by() \
            .values_list('id', flat=True)
        asset_ids.update(list(_asset_ids))

        return Asset.objects.filter(id__in=asset_ids)


class UserPermNodeUtil:

    def __init__(self, user):
        self.user = user
        self.perm_ids = AssetPermissionUtil().get_permissions_for_user(self.user, flat=True)

    def get_favorite_node(self):
        assets_amount = UserPermAssetUtil(self.user).get_favorite_assets().count()
        return PermNode.get_favorite_node(assets_amount)

    def get_ungrouped_node(self):
        assets_amount = UserPermAssetUtil(self.user).get_direct_assets().count()
        return PermNode.get_ungrouped_node(assets_amount)

    def get_top_level_nodes(self, with_unfolded_node=False):
        # 是否有节点展开, 展开的节点
        unfolded_node = None
        nodes = self.get_special_nodes()
        real_nodes = self._get_perm_node_children_from_relation(key='')
        nodes.extend(real_nodes)
        if len(real_nodes) == 1:
            unfolded_node = real_nodes[0]
            children = self.get_node_children(unfolded_node.key)
            nodes.extend(children)
        if with_unfolded_node:
            return nodes, unfolded_node
        else:
            return nodes

    def get_special_nodes(self):
        nodes = []
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            ung_node = self.get_ungrouped_node()
            nodes.append(ung_node)
        fav_node = self.get_favorite_node()
        nodes.append(fav_node)
        return nodes

    def get_node_children(self, key):
        if not key:
            return self.get_top_level_nodes()

        if key in [PermNode.FAVORITE_NODE_KEY, PermNode.UNGROUPED_NODE_KEY]:
            return PermNode.objects.none()

        node = PermNode.objects.get(key=key)
        node.compute_node_from_and_assets_amount(self.user)
        if node.node_from == node.NodeFrom.granted:
            """ 直接授权的节点, 直接从完整资产树获取子节点 """
            children = PermNode.objects.filter(parent_key=key)
        elif node.node_from in (node.NodeFrom.asset, node.NodeFrom.child):
            """ 间接授权的节点, 从 Relation 表中获取子节点 """
            children = self._get_perm_node_children_from_relation(key)
        else:
            children = PermNode.objects.none()
        children = sorted(children, key=lambda x: x.value)
        return children

    def _get_perm_node_children_from_relation(self, key):
        """ 获取授权节点的子节点, 从用户授权节点关系表中获取 """
        children = PermNode.objects.filter(granted_node_rels__user=self.user, parent_key=key)
        children = children.annotate(**PermNode.annotate_granted_node_rel_fields).distinct()
        for node in children:
            node.assets_amount = node.granted_assets_amount
        return children

    @timeit
    def get_whole_tree_nodes(self, with_special=True):
        user_nodes = PermNode.objects.filter(granted_node_rels__user=self.user)
        user_nodes = user_nodes.annotate(**PermNode.annotate_granted_node_rel_fields).distinct()

        key_node_mapper = {}
        q_nodes_descendant = Q()
        for node in user_nodes:
            node.assets_amount = node.granted_assets_amount
            key_node_mapper[node.key] = node
            if node.node_from == node.NodeFrom.granted:
                """ 直接授权的节点, 增加后代节点的过滤条件 """
                q_nodes_descendant |= Q(key__startswith=f'{node.key}:')
        if q_nodes_descendant:
            descendant_nodes = PermNode.objects.filter(q_nodes_descendant)
            for node in descendant_nodes:
                key_node_mapper[node.key] = node

        nodes = []
        if with_special:
            special_nodes = self.get_special_nodes()
            nodes.extend(special_nodes)
        nodes.extend(list(key_node_mapper.values()))

        return nodes
