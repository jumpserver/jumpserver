from collections import defaultdict
from typing import List, Tuple

from django.conf import settings
from django.db.models import Q, QuerySet
from django.utils.translation import gettext as _

from users.models import User
from assets.utils import NodeAssetsUtil
from assets.models import (
    Asset,
    FavoriteAsset,
    AssetQuerySet,
    NodeQuerySet
)
from orgs.utils import (
    tmp_to_org,
    current_org,
    ensure_in_real_or_default_org,
)
from common.db.models import output_as_string, UnionQuerySet
from common.utils import get_logger
from common.utils.common import lazyproperty, timeit

from perms.models import (
    AssetPermission,
    PermNode,
    UserAssetGrantedTreeNodeRelation
)
from .permission import AssetPermissionUtil

NodeFrom = UserAssetGrantedTreeNodeRelation.NodeFrom
NODE_ONLY_FIELDS = ('id', 'key', 'parent_key', 'org_id')

logger = get_logger(__name__)


class UserGrantedUtilsBase:
    user: User

    def __init__(self, user, asset_perm_ids=None):
        self.user = user
        self._asset_perm_ids = asset_perm_ids and set(asset_perm_ids)

    @lazyproperty
    def asset_perm_ids(self) -> set:
        if self._asset_perm_ids:
            return self._asset_perm_ids

        asset_perm_ids = AssetPermissionUtil().get_permissions_for_user(self.user, flat=True)
        return asset_perm_ids


class UserGrantedAssetsQueryUtils(UserGrantedUtilsBase):

    def get_favorite_assets(self) -> QuerySet:
        assets = self.get_all_granted_assets()
        asset_ids = FavoriteAsset.objects.filter(user=self.user).values_list('asset_id', flat=True)
        assets = assets.filter(id__in=list(asset_ids))
        return assets

    def get_ungroup_assets(self) -> AssetQuerySet:
        return self.get_direct_granted_assets()

    def get_direct_granted_assets(self) -> AssetQuerySet:
        queryset = Asset.objects.order_by().filter(
            granted_by_permissions__id__in=self.asset_perm_ids
        ).distinct()
        return queryset

    def get_direct_granted_nodes_assets(self) -> AssetQuerySet:
        granted_node_ids = AssetPermission.nodes.through.objects.filter(
            assetpermission_id__in=self.asset_perm_ids
        ).values_list('node_id', flat=True).distinct()
        granted_node_ids = list(granted_node_ids)
        granted_nodes = PermNode.objects.filter(id__in=granted_node_ids).only('id', 'key')
        queryset = PermNode.get_nodes_all_assets(*granted_nodes)
        return queryset

    def get_all_granted_assets(self) -> QuerySet:
        nodes_assets = self.get_direct_granted_nodes_assets()
        assets = self.get_direct_granted_assets()
        # queryset = UnionQuerySet(nodes_assets, assets)
        # return queryset
        node_asset_ids = nodes_assets.values_list('id', flat=True)
        direct_asset_ids = assets.values_list('id', flat=True)
        asset_ids = list(node_asset_ids) + list(direct_asset_ids)
        asset = Asset.objects.filter(id__in=asset_ids)
        return asset

    def get_node_all_assets(self, id) -> Tuple[PermNode, QuerySet]:
        node = PermNode.objects.get(id=id)
        granted_status = node.get_granted_status(self.user)
        if granted_status == NodeFrom.granted:
            assets = PermNode.get_nodes_all_assets(node)
            return node, assets
        elif granted_status in (NodeFrom.asset, NodeFrom.child):
            node.use_granted_assets_amount()
            assets = self._get_indirect_granted_node_all_assets(node)
            return node, assets
        else:
            node.assets_amount = 0
            return node, Asset.objects.none()

    def get_node_assets(self, key) -> AssetQuerySet:
        node = PermNode.objects.get(key=key)
        granted_status = node.get_granted_status(self.user)

        if granted_status == NodeFrom.granted:
            assets = Asset.objects.order_by().filter(nodes__id=node.id)
        elif granted_status == NodeFrom.asset:
            assets = self._get_indirect_granted_node_assets(node.id)
        else:
            assets = Asset.objects.none()
        assets = assets.order_by('name')
        return assets

    def _get_indirect_granted_node_assets(self, id) -> AssetQuerySet:
        assets = Asset.objects.order_by().filter(nodes__id=id).distinct() & self.get_direct_granted_assets()
        return assets

    def _get_indirect_granted_node_all_assets(self, node) -> QuerySet:
        """
        此算法依据 `UserAssetGrantedTreeNodeRelation` 的数据查询
        1. 查询该节点下的直接授权节点
        2. 查询该节点下授权资产关联的节点
        """
        user = self.user

        # 查询该节点下的授权节点
        granted_nodes = UserAssetGrantedTreeNodeRelation.objects.filter(
            user=user, node_from=NodeFrom.granted
        ).filter(
            Q(node_key__startswith=f'{node.key}:')
        ).only('node_id', 'node_key')

        for n in granted_nodes:
            n.id = n.node_id

        node_assets = PermNode.get_nodes_all_assets(*granted_nodes)

        # 查询该节点下的资产授权节点
        only_asset_granted_node_ids = UserAssetGrantedTreeNodeRelation.objects.filter(
            user=user, node_from=NodeFrom.asset
        ).filter(
            Q(node_key__startswith=f'{node.key}:')
        ).values_list('node_id', flat=True)

        only_asset_granted_node_ids = list(only_asset_granted_node_ids)
        if node.node_from == NodeFrom.asset:
            only_asset_granted_node_ids.append(node.id)

        assets = Asset.objects.filter(
            nodes__id__in=only_asset_granted_node_ids,
            granted_by_permissions__id__in=self.asset_perm_ids
        ).distinct().order_by()
        granted_assets = UnionQuerySet(node_assets, assets)
        return granted_assets


class UserGrantedNodesQueryUtils(UserGrantedUtilsBase):
    def sort(self, nodes):
        nodes = sorted(nodes, key=lambda x: x.value)
        return nodes

    def get_node_children(self, key):
        if not key:
            return self.get_top_level_nodes()

        nodes = PermNode.objects.none()
        if key in [PermNode.FAVORITE_NODE_KEY, PermNode.UNGROUPED_NODE_KEY]:
            return nodes

        node = PermNode.objects.get(key=key)
        granted_status = node.get_granted_status(self.user)
        if granted_status == NodeFrom.granted:
            nodes = PermNode.objects.filter(parent_key=key)
        elif granted_status in (NodeFrom.asset, NodeFrom.child):
            nodes = self.get_indirect_granted_node_children(key)
        nodes = self.sort(nodes)
        return nodes

    def get_indirect_granted_node_children(self, key):
        """
        获取用户授权树中未授权节点的子节点
        只匹配在 `UserAssetGrantedTreeNodeRelation` 中存在的节点
        """
        user = self.user
        nodes = PermNode.objects.filter(
            granted_node_rels__user=user,
            parent_key=key
        ).annotate(
            **PermNode.annotate_granted_node_rel_fields
        ).distinct()

        # 设置节点授权资产数量
        for node in nodes:
            node.use_granted_assets_amount()
        return nodes

    def get_top_level_nodes(self):
        nodes = self.get_special_nodes()
        real_nodes = self.get_indirect_granted_node_children('')
        nodes.extend(real_nodes)
        if len(real_nodes) == 1:
            children = self.get_node_children(real_nodes[0].key)
            nodes.extend(children)
        return nodes

    def get_ungrouped_node(self):
        assets_util = UserGrantedAssetsQueryUtils(self.user, self.asset_perm_ids)
        assets_amount = assets_util.get_direct_granted_assets().count()
        return PermNode.get_ungrouped_node(assets_amount)

    def get_favorite_node(self):
        assets_query_utils = UserGrantedAssetsQueryUtils(self.user, self.asset_perm_ids)
        assets_amount = assets_query_utils.get_favorite_assets().values_list('id').count()
        return PermNode.get_favorite_node(assets_amount)

    @staticmethod
    def get_root_node():
        name = _('My assets')
        node = {
            'id': '',
            'name': name,
            'title': name,
            'pId': '',
            'open': True,
            'isParent': True,
            'meta': {
                'type': 'root'
            }
        }
        return node

    def get_special_nodes(self):
        nodes = []
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            ungrouped_node = self.get_ungrouped_node()
            nodes.append(ungrouped_node)
        favorite_node = self.get_favorite_node()
        nodes.append(favorite_node)
        return nodes

    @timeit
    def get_whole_tree_nodes(self, with_special=True):
        """
        这里的 granted nodes, 是整棵树需要的node，推算出来的也算
        :param with_special:
        :return:
        """
        nodes = PermNode.objects.filter(granted_node_rels__user=self.user) \
            .annotate(**PermNode.annotate_granted_node_rel_fields) \
            .distinct()

        key_to_node_mapper = {}
        nodes_descendant_q = Q()

        for node in nodes:
            node.use_granted_assets_amount()
            key_to_node_mapper[node.key] = node

            if node.node_from == NodeFrom.granted:
                # 直接授权的节点
                # 增加查询后代节点的过滤条件
                nodes_descendant_q |= Q(key__startswith=f'{node.key}:')

        if nodes_descendant_q:
            descendant_nodes = PermNode.objects.filter(
                nodes_descendant_q
            )
            for node in descendant_nodes:
                key_to_node_mapper[node.key] = node

        all_nodes = []
        if with_special:
            special_nodes = self.get_special_nodes()
            all_nodes.extend(special_nodes)
        all_nodes.extend(key_to_node_mapper.values())
        return all_nodes
