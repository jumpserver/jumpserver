from typing import List, Tuple
from itertools import chain

from django.core.cache import cache
from django.conf import settings
from django.db.models import Q

from common.utils.common import lazyproperty
from assets.tree import Tree
from common.utils import get_logger
from common.decorator import on_transaction_commit
from orgs.utils import tmp_to_org, current_org, ensure_not_in_root_org
from assets.models import (
    Node, Asset, FavoriteAsset, NodeAssetRelatedRecord,
    AssetQuerySet, NodeQuerySet
)
from orgs.models import Organization
from perms.models import UserGrantedMappingNode, AssetPermission, PermNode
from users.models import User
from perms.locks import UserGrantedTreeRebuildLock

logger = get_logger(__name__)


def get_user_all_asset_perm_ids(user) -> set:
    group_ids = user.groups.through.objects.filter(user_id=user.id) \
        .distinct().values_list('usergroup_id', flat=True)
    asset_perm_ids = set()
    asset_perm_ids.update(
        AssetPermission.users.through.objects.filter(
            user_id=user.id).distinct().values_list('assetpermission_id', flat=True))
    asset_perm_ids.update(
        AssetPermission.user_groups.through.objects.filter(
            usergroup_id__in=group_ids).distinct().values_list('assetpermission_id', flat=True))
    return asset_perm_ids


class UserGrantedTreeRefreshController:
    key_template = 'perms.user.asset.node.tree.need_refresh_orgs.<user_id:{user_id}>'

    def __init__(self, user):
        self.user = user
        self.key = self.key_template.format({'user_id': user.id})
        self.client = self.get_redis_client()

    @classmethod
    def get_redis_client(cls):
        return cache.client.get_client(write=True)

    def get_need_refresh_org_ids(self):
        org_ids = self.client.smembers(self.key)
        return {org_id.decode() for org_id in org_ids}

    def get_and_delete_need_refresh_org_ids(self):
        with self.client.pipeline(transaction=False) as p:
            p.smembers(self.key)
            p.delete(self.key)
            ret = p.execute()
            org_ids = ret[0] or ()
            org_ids = {org_id.decode() for org_id in org_ids}
            logger.info(f'Get and delete <user_id:{self.user.id}> in <org_ids:{org_ids}> need refresh mark')
            return org_ids

    @on_transaction_commit
    def add_need_refresh_org_ids(self, *org_ids):
        self.client.sadd(self.key, *org_ids)
        logger.info(f'Mark <user_id:{self.user.id}> in <org_ids:{org_ids}> need refresh')

    @classmethod
    @on_transaction_commit
    def add_need_refresh_orgs_for_users(cls, org_ids, user_ids):
        client = cls.get_redis_client()

        with client.pipeline(transaction=False) as p:
            for user_id in user_ids:
                key = cls.key_template.format({'user_id': user_id})
                p.sadd(key, *org_ids)

            p.execute()
        logger.info(f'Mark <user_ids:{user_ids}> in <org_ids:{org_ids}> need refresh')

    @classmethod
    def add_need_refresh_on_nodes_assets_relate_change(cls, node_ids, asset_ids):
        """
        1，计算与这些资产有关的授权
        2，计算与这些节点以及祖先节点有关的授权
        """
        ensure_not_in_root_org()

        node_ids = set(node_ids)
        ancestor_node_keys = set()

        asset_perm_ids = set()

        nodes = Node.objects.filter(id__in=node_ids).only('id', 'key')
        for node in nodes:
            ancestor_node_keys.update(node.get_ancestor_keys())
        node_ids.update(
            Node.objects.filter(key__in=ancestor_node_keys).values_list('id', flat=True)
        )

        asset_perm_ids.update(
            AssetPermission.nodes.through.objects.filter(
                node_id__in=node_ids).values_list('assetpermission_id', flat=True)
        )
        asset_perm_ids.update(
            AssetPermission.assets.through.objects.filter(
                asset_id__in=asset_ids).values_list('assetpermission_id', flat=True)
        )
        cls.add_need_refresh_by_asset_perm_ids(asset_perm_ids)

    @classmethod
    def add_need_refresh_by_asset_perm_ids(cls, asset_perm_ids):
        ensure_not_in_root_org()

        group_ids = AssetPermission.user_groups.through.objects.filter(
            assetpermission_id__in=asset_perm_ids).values_list('usergroup_id', flat=True)

        user_ids = set()
        user_ids.update(
            AssetPermission.users.through.objects.filter(
                assetpermission_id__in=asset_perm_ids).values_list('user_id', flat=True)
        )
        user_ids.update(
            User.groups.through.objects.filter(usergroup_id__in=group_ids).values_list('user_id', flat=True)
        )

        cls.add_need_refresh_orgs_for_users(
            [current_org.id], user_ids
        )

    def refresh_if_need(self, force=False):
        user = self.user
        exists = UserGrantedMappingNode.objects.filter(user=user).exists()

        if force or not exists:
            orgs = [user.orgs, Organization.default()]
        else:
            org_ids = self.get_and_delete_need_refresh_org_ids()
            orgs = [Organization.get_instance(org_id) for org_id in org_ids]

        for org in orgs:
            with tmp_to_org(org):
                granted_tree_utils = UserGrantedTreeBuildUtils(user)
                granted_tree_utils.rebuild_user_granted_tree()


class UserGrantedUtilsBase:
    user: User

    def __init__(self, user, asset_perm_ids=None):
        self.user = user
        self._asset_perm_ids = asset_perm_ids

    @lazyproperty
    def asset_perm_ids(self) -> set:
        if self._asset_perm_ids:
            return self._asset_perm_ids

        asset_perm_ids = get_user_all_asset_perm_ids(self.user)
        return asset_perm_ids


class UserGrantedTreeBuildUtils(UserGrantedUtilsBase):
    node_only_fields = ('id', 'key', 'parent_key', 'assets_amount')

    @lazyproperty
    def direct_granted_nodes(self) -> NodeQuerySet:
        # 查询直接授权节点
        nodes = PermNode.objects.filter(
            granted_by_permissions__id__in=self.asset_perm_ids
        ).distinct().only(*self.node_only_fields)
        return nodes

    @lazyproperty
    def direct_granted_asset_ids(self) -> list:
        asset_ids = Asset.org_objects.filter(
            granted_by_permissions__id__in=self.asset_perm_ids
        ).distinct().values_list('id', flat=True)
        asset_ids = list(asset_ids)
        return asset_ids

    def rebuild_user_granted_tree(self):
        ensure_not_in_root_org()

        user = self.user
        org_id = current_org.id

        with UserGrantedTreeRebuildLock(org_id, user.id):
            # 先删除旧的授权树🌲
            UserGrantedMappingNode.objects.filter(
                user=user,
                node__org_id=org_id
            ).delete()

            if not self.asset_perm_ids:
                # 没有授权直接返回
                return

            nodes = self.compute_perm_nodes_tree()
            self.compute_node_assets_amount(nodes)
            self.create_mapping_nodes(nodes)

    def compute_perm_nodes_tree(self) -> list:
        node_only_fields = ('id', 'key', 'parent_key', 'assets_amount')

        # 查询直接授权节点
        nodes = self.direct_granted_nodes

        # 授权的节点 key 集合
        granted_key_set = {_node.key for _node in nodes}

        def _has_ancestor_granted(node: PermNode):
            """
            判断一个节点是否有授权过的祖先节点
            """
            ancestor_keys = set(node.get_ancestor_keys(with_self=True))
            return ancestor_keys & granted_key_set

        key2leaf_nodes_mapper = {}

        # 给授权节点设置 is_granted 标识，同时去重
        for node in nodes:
            if _has_ancestor_granted(node):
                continue

            node.is_granted = True
            key2leaf_nodes_mapper[node.key] = node

        # 查询授权资产关联的节点设置
        def process_direct_granted_assets():
            # 查询直接授权资产
            asset_ids = self.direct_granted_asset_ids
            # 查询授权资产关联的节点设置
            granted_asset_nodes = Node.objects.filter(
                assets__id__in=asset_ids
            ).distinct().only(*node_only_fields)

            # 给资产授权关联的节点设置 is_asset_granted 标识，同时去重
            for node in granted_asset_nodes:
                if _has_ancestor_granted(node):
                    continue
                node.is_asset_granted = True
                key2leaf_nodes_mapper[node.key] = node

        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            process_direct_granted_assets()

        leaf_nodes = key2leaf_nodes_mapper.values()

        # 计算所有祖先节点
        ancestor_keys = set()
        for node in leaf_nodes:
            ancestor_keys.update(node.get_ancestor_keys())

        # 从祖先节点 key 中去掉同时也是叶子节点的 key
        ancestor_keys -= key2leaf_nodes_mapper.keys()
        # 查出祖先节点
        ancestors = Node.objects.filter(key__in=ancestor_keys).only(*node_only_fields)
        return [*leaf_nodes, *ancestors]

    def create_mapping_nodes(self, nodes):
        user = self.user
        to_create = []
        for node in nodes:
            to_create.append(UserGrantedMappingNode(
                user=user,
                node=node,
                key=node.key,
                parent_key=node.parent_key,
                granted=node.is_granted,
                asset_granted=node.is_asset_granted,
                assets_amount=node.assets_amount,
            ))

        UserGrantedMappingNode.objects.bulk_create(to_create)

    def compute_node_assets_amount(self, nodes: List[PermNode]):
        """
        这里计算的是一个组织的
        """
        if len(nodes) == 1:
            node = nodes[0]
            if node.is_granted and node.key.isdigit():
                # 直接授权了跟节点
                node.granted_assets_amount = node.assets_amount
                return

        asset_perm_ids = self.asset_perm_ids

        direct_granted_node_ids = [
            node.id for node in nodes
            if node.is_granted
        ]

        # 根据资产授权，取出所有直接授权的资产
        direct_granted_asset_ids = set(
            AssetPermission.assets.through.objects.filter(
                assetpermission_id__in=asset_perm_ids).values_list('asset_id', flat=True)
        )

        # 直接授权资产，取节点与资产的关系
        node_asset_pairs_1 = Asset.nodes.through.objects.filter(asset_id__in=direct_granted_asset_ids).values_list(
            'node_id', 'asset_id')
        # 直接授权的节点，取节点与资产的关系
        node_asset_pairs_2 = NodeAssetRelatedRecord.objects.filter(node_id__in=direct_granted_node_ids).values_list(
            'node_id', 'asset_id')

        tree = Tree(nodes, chain(node_asset_pairs_1, node_asset_pairs_2))
        tree.build_tree()
        tree.compute_tree_node_assets_amount()

        for node in nodes:
            assets_amount = tree.key_tree_node_mapper[node.key].assets_amount
            node.assets_amount = assets_amount

    def get_whole_tree_nodes(self) -> list:
        nodes = self.compute_perm_nodes_tree()
        self.compute_node_assets_amount(nodes)

        # 查询直接授权节点的子节点
        q = Q()
        for node in self.direct_granted_nodes:
            q |= Q(key__startswith=f'{node.key}:')

        if q:
            descendant_nodes = Node.objects.filter(q).distinct()
        else:
            descendant_nodes = Node.objects.none()
        nodes.extend(descendant_nodes)
        return nodes


class UserGrantedAssetsQueryUtils(UserGrantedUtilsBase):

    def get_favorite_assets(self) -> AssetQuerySet:
        favorite_asset_ids = FavoriteAsset.objects.filter(
            user=self.user).values_list('asset_id', flat=True)
        favorite_asset_ids = list(favorite_asset_ids)
        assets = self.get_all_granted_assets().filter(id__in=favorite_asset_ids)
        return assets
    
    def get_ungroup_assets(self) -> AssetQuerySet:
        return self.get_direct_granted_assets()

    def get_direct_granted_assets(self) -> AssetQuerySet:
        queryset = Asset.org_objects.filter(
            granted_by_permissions__id__in=self.asset_perm_ids
        ).distinct()
        return queryset

    def get_direct_granted_nodes_assets(self) -> AssetQuerySet:
        granted_node_ids = AssetPermission.nodes.through.objects.filter(
            assetpermission_id__in=self.asset_perm_ids
        ).values_list('node_id', flat=True).distinct()
        queryset = Asset.org_objects.filter(
            nodes_related_records__node_id__in=granted_node_ids
        )
        return queryset

    def get_all_granted_assets(self) -> AssetQuerySet:
        queryset = self.get_direct_granted_nodes_assets() | self.get_direct_granted_assets()
        return queryset

    def get_node_all_assets(self, id) -> Tuple[PermNode, AssetQuerySet]:
        node = PermNode.get_node_with_mapping_info(self.user, id)
        granted_status = PermNode.get_node_granted_status(self.user, node.key)
        if granted_status == PermNode.GRANTED_DIRECT:
            assets = Asset.org_objects.filter(nodes_related_records__node_id=node.id)
            return node, assets
        elif granted_status == PermNode.GRANTED_INDIRECT:
            node.use_mapping_assets_amount()
            return node, self._get_indirect_granted_node_all_assets(node.key)
        else:
            node.assets_amount = 0
            return node, Asset.org_objects.none()

    def get_node_assets(self, key) -> AssetQuerySet:
        node = PermNode.objects.get(key=key)
        granted_status = PermNode.get_node_granted_status(self.user, node.key)

        if granted_status == PermNode.GRANTED_DIRECT:
            assets = Asset.org_objects.filter(nodes_id=node.id)
            return assets
        elif granted_status == PermNode.GRANTED_INDIRECT:
            return self._get_indirect_granted_node_assets(node.id)
        else:
            return Asset.org_objects.none()

    def _get_indirect_granted_node_assets(self, id) -> AssetQuerySet:
        assets = Asset.org_objects.filter(nodes_id=id) & self.get_direct_granted_assets()
        return assets

    def _get_indirect_granted_node_all_assets(self, key) -> AssetQuerySet:
        """
        此算法依据 `UserGrantedMappingNode` 的数据查询
        1. 查询该节点下的直接授权节点
        2. 查询该节点下授权资产关联的节点
        """
        user = self.user

        # 查询该节点下的授权节点
        granted_node_ids = UserGrantedMappingNode.objects.filter(
            user=user, granted=True,
        ).filter(
            Q(key__startswith=f'{key}:') | Q(key=key)
        ).values_list('node_id', flat=True)

        granted_node_assets = Asset.org_objects.filter(nodes_related_records__node_id__in=granted_node_ids)

        # 查询该节点下的资产授权节点
        only_asset_granted_node_ids = UserGrantedMappingNode.objects.filter(
            user=user,
            asset_granted=True,
            granted=False,
        ).filter(Q(key__startswith=f'{key}:') | Q(key=key)).values_list('node_id', flat=True)

        direct_granted_assets = Asset.org_objects.filter(
            nodes__id__in=only_asset_granted_node_ids,
            granted_by_permissions__id__in=self.asset_perm_ids
        )

        return granted_node_assets | direct_granted_assets


class UserGrantedNodesQueryUtils(UserGrantedUtilsBase):
    def get_node_children(self, key):
        if not key:
            return self.get_top_level_nodes()

        granted_status = PermNode.get_node_granted_status(self.user, key)
        if granted_status == PermNode.GRANTED_DIRECT:
            return PermNode.objects.filter(parent_key=key)
        elif granted_status == PermNode.GRANTED_INDIRECT:
            return self.get_indirect_granted_node_children(key)
        else:
            return PermNode.objects.none()

    def get_indirect_granted_node_children(self, key):
        """
        获取用户授权树中未授权节点的子节点
        只匹配在 `UserGrantedMappingNode` 中存在的节点
        """
        user = self.user
        nodes = PermNode.objects.filter(
            mapping_nodes__user=user,
            parent_key=key
        ).annotate(
            **PermNode.annotate_mapping_node_fields
        ).distinct()

        # 设置节点授权资产数量
        for node in nodes:
            if not node.is_granted:
                node.use_mapping_assets_amount()
        return nodes

    def get_top_level_nodes(self):
        nodes = self.get_special_nodes()
        nodes.extend(self.get_indirect_granted_node_children(''))
        return nodes

    def get_ungrouped_node(self):
        assets_util = UserGrantedAssetsQueryUtils(self.user, self.asset_perm_ids)
        assets_amount = assets_util.get_direct_granted_assets().count()
        return PermNode.get_ungrouped_node(assets_amount)

    def get_favorite_node(self):
        assets_query_utils = UserGrantedAssetsQueryUtils(self.user, self.asset_perm_ids)
        assets_amount = assets_query_utils.get_favorite_assets().values_list('id').count()
        return PermNode.get_favorite_node(assets_amount)

    def get_special_nodes(self):
        nodes = []
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            ungrouped_node = self.get_ungrouped_node()
            nodes.append(ungrouped_node)
        favorite_node = self.get_favorite_node()
        nodes.append(favorite_node)
        return nodes

    def get_whole_tree_nodes(self, with_special=True):
        """
        这里的 granted nodes, 是整棵树需要的node，推算出来的也算
        :param user:
        :return:
        """
        # 获取 `UserGrantedMappingNode` 中对应的 `Node`
        nodes = PermNode.objects.filter(
            mapping_nodes__user=self.user,
        ).annotate(
            **PermNode.annotate_mapping_node_fields
        ).distinct()

        key_to_node_mapper = {}
        nodes_descendant_q = Q()

        for node in nodes:
            if not node.is_granted:
                # 未授权的节点资产数量设置为 `UserGrantedMappingNode` 中的数量
                node.use_mapping_assets_amount()
            else:
                # 直接授权的节点
                # 增加查询后代节点的过滤条件
                nodes_descendant_q |= Q(key__startswith=f'{node.key}:')
            key_to_node_mapper[node.key] = node

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
