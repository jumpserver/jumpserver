from assets.models import FavoriteAsset, Asset

from perms.models import AssetPermission, PermNode, UserAssetGrantedTreeNodeRelation

from .permission import AssetPermissionUtil


__all__ = ['UserPermAssetUtil']


class UserPermAssetUtil:

    def __init__(self, user):
        self.user = user
        self.perm_ids = AssetPermissionUtil().get_permissions_for_user(self.user, flat=True)

    def get_favorite_assets(self):
        assets = self.get_all_assets()
        asset_ids = FavoriteAsset.objects.filter(user=self.user).values_list('asset_id', flat=True)
        assets = assets.filter(id__in=list(asset_ids))
        return assets

    def get_ungroup_assets(self):
        return self.get_direct_assets(self.perm_ids)

    def get_all_assets(self):
        return self.get_all_assets_by_perms(self.perm_ids)

    @classmethod
    def get_all_assets_by_perms(cls, perm_ids):
        node_asset_ids = cls.get_perm_nodes_assets(perm_ids, flat=True)
        direct_asset_ids = cls.get_direct_assets(perm_ids, flat=True)
        asset_ids = list(node_asset_ids) + list(direct_asset_ids)
        assets = Asset.objects.filter(id__in=asset_ids)
        return assets

    @classmethod
    def get_perm_nodes_assets(cls, perm_ids, flat=False):
        """ 获取所有授权节点下的资产 """
        node_ids = AssetPermission.nodes.through.objects \
            .filter(assetpermission_id__in=perm_ids) \
            .values_list('node_id', flat=True) \
            .distinct()
        node_ids = list(node_ids)
        nodes = PermNode.objects.filter(id__in=node_ids).only('id', 'key')
        assets = PermNode.get_nodes_all_assets(*nodes)
        if flat:
            return assets.values_list('id', flat=True)
        return assets

    @classmethod
    def get_direct_assets(cls, perm_ids, flat=False):
        """ 获取直接授权的资产 """
        assets = Asset.objects.order_by() \
            .filter(granted_by_permissions__id__in=perm_ids) \
            .distinct()
        if flat:
            return assets.values_list('id', flat=True)
        return assets

    def get_node_assets(self, key):
        node = PermNode.objects.get(key=key)
        node.compute_node_from_and_assets_amount()
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
            assets = PermNode.get_nodes_all_assets()
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
            .filter(node_key__startwith=f'{node.key}:', node_from=node.NodeFrom.granted) \
            .only('node_id', 'node_key')
        for n in children_from_granted:
            n.id = n.node_id
        _assets = PermNode.get_nodes_all_assets(*children_from_granted)
        _asset_ids = _assets.values_list('id', flat=True)
        asset_ids.update(list(_asset_ids))

        # 查询节点下资产授权的节点
        children_from_assets = UserAssetGrantedTreeNodeRelation.objects \
            .filter(user=self.user) \
            .filter(node_key__startwith=f'{node.key}:', node_from=node.NodeFrom.asset) \
            .values_list('node_id', flat=True)
        children_from_assets = set(children_from_assets)
        if node.node_from == node.NodeFrom.asset:
            children_from_assets.add(node.id)
        _asset_ids = Asset.objects \
            .filter(node__id__in=children_from_assets) \
            .filter(granted_by_permissions__id__in=self.perm_ids) \
            .distinct() \
            .order_by() \
            .values_list('id', flat=True)
        asset_ids.update(list(_asset_ids))

        return Asset.objects.filter(id__in=asset_ids)


class UserPermNodeUtil:
    pass
