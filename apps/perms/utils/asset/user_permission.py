from collections import defaultdict
from typing import List, Tuple
from itertools import chain

from django.core.cache import cache
from django.conf import settings
from django.db.models import Q, QuerySet

from common.utils.common import lazyproperty, timeit
from assets.tree import Tree
from perms.tree import GrantedTree
from common.utils import get_logger
from common.decorator import on_transaction_commit
from orgs.utils import tmp_to_org, current_org, ensure_in_real_or_default_org
from assets.models import (
    Asset, FavoriteAsset, NodeAssetRelatedRecord,
    AssetQuerySet, NodeQuerySet
)
from orgs.models import Organization
from perms.models import (
    AssetPermission, PermNode, UserAssetGrantedTreeNodeRelation,
    NodeAssetThrouth,
)
from users.models import User
from perms.locks import UserGrantedTreeRebuildLock

NodeFrom = UserAssetGrantedTreeNodeRelation.NodeFrom
NODE_ONLY_FIELDS = ('id', 'key', 'parent_key', 'assets_amount')

logger = get_logger(__name__)


def get_user_all_asset_perm_ids(user) -> set:
    group_ids = user.groups.through.objects.filter(user_id=user.id) \
        .distinct().values_list('usergroup_id', flat=True)
    group_ids = list(group_ids)
    asset_perm_ids = set()
    asset_perm_ids.update(
        AssetPermission.users.through.objects.filter(
            user_id=user.id).distinct().values_list('assetpermission_id', flat=True))
    asset_perm_ids.update(
        AssetPermission.user_groups.through.objects.filter(
            usergroup_id__in=group_ids).distinct().values_list('assetpermission_id', flat=True))
    return asset_perm_ids


class QuerySetStage:
    def __init__(self):
        self._prefetch_related = set()
        self._only = ()
        self._filters = []
        self._querysets_and = []
        self._querysets_or = []
        self._order_by = None
        self._annotate = []
        self._before_union_merge_funs = set()
        self._after_union_merge_funs = set()

    def annotate(self, *args, **kwargs):
        self._annotate.append((args, kwargs))
        self._before_union_merge_funs.add(self._merge_annotate)
        return self

    def prefetch_related(self, *lookups):
        self._prefetch_related.update(lookups)
        self._before_union_merge_funs.add(self._merge_prefetch_related)
        return self

    def only(self, *fields):
        self._only = fields
        self._before_union_merge_funs.add(self._merge_only)
        return self

    def order_by(self, *field_names):
        self._order_by = field_names
        self._after_union_merge_funs.add(self._merge_order_by)
        return self

    def filter(self, *args, **kwargs):
        self._filters.append((args, kwargs))
        self._before_union_merge_funs.add(self._merge_filters)
        return self

    def and_with_queryset(self, qs: QuerySet):
        assert isinstance(qs, QuerySet), f'Must be `QuerySet`'
        self._order_by = qs.query.order_by
        self._after_union_merge_funs.add(self._merge_order_by)
        self._querysets_and.append(qs.order_by())
        self._before_union_merge_funs.add(self._merge_querysets_and)
        return self

    def or_with_queryset(self, qs: QuerySet):
        assert isinstance(qs, QuerySet), f'Must be `QuerySet`'
        self._order_by = qs.query.order_by
        self._after_union_merge_funs.add(self._merge_order_by)
        self._querysets_or.append(qs.order_by())
        self._before_union_merge_funs.add(self._merge_querysets_or)
        return self

    def merge_multi_before_union(self, *querysets):
        ret = []
        for qs in querysets:
            qs = self.merge_before_union(qs)
            ret.append(qs)
        return ret

    def _merge_only(self, qs: QuerySet):
        if self._only:
            qs = qs.only(*self._only)
        return qs

    def _merge_filters(self, qs: QuerySet):
        if self._filters:
            for args, kwargs in self._filters:
                qs = qs.filter(*args, **kwargs)
        return qs

    def _merge_querysets_and(self, qs: QuerySet):
        if self._querysets_and:
            for qs_and in self._querysets_and:
                qs &= qs_and
        return qs

    def _merge_annotate(self, qs: QuerySet):
        if self._annotate:
            for args, kwargs in self._annotate:
                qs = qs.annotate(*args, **kwargs)
        return qs

    def _merge_querysets_or(self, qs: QuerySet):
        if self._querysets_or:
            for qs_or in self._querysets_or:
                qs |= qs_or
        return qs

    def _merge_prefetch_related(self, qs: QuerySet):
        if self._prefetch_related:
            qs = qs.prefetch_related(*self._prefetch_related)
        return qs

    def _merge_order_by(self,  qs: QuerySet):
        if self._order_by is not None:
            qs = qs.order_by(*self._order_by)
        return qs

    def merge_before_union(self, qs: QuerySet) -> QuerySet:
        assert isinstance(qs, QuerySet), f'Must be `QuerySet`'
        for fun in self._before_union_merge_funs:
            qs = fun(qs)
        return qs

    def merge_after_union(self, qs: QuerySet) -> QuerySet:
        for fun in self._after_union_merge_funs:
            qs = fun(qs)
        return qs

    def merge(self, qs: QuerySet) -> QuerySet:
        qs = self.merge_before_union(qs)
        qs = self.merge_after_union(qs)
        return qs


class UserGrantedTreeRefreshController:
    key_template = 'perms.user.asset.node.tree.need_refresh_orgs.<user_id:{user_id}>'

    def __init__(self, user):
        self.user = user
        self.key = self.key_template.format(user_id = user.id)
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
        org_ids = [str(org_id) for org_id in org_ids]

        with client.pipeline(transaction=False) as p:
            for user_id in user_ids:
                key = cls.key_template.format(user_id=user_id)
                p.sadd(key, *org_ids)

            p.execute()
        logger.info(f'Mark <user_ids:{user_ids}> in <org_ids:{org_ids}> need refresh')

    @classmethod
    def add_need_refresh_on_nodes_assets_relate_change(cls, node_ids, asset_ids):
        """
        1，计算与这些资产有关的授权
        2，计算与这些节点以及祖先节点有关的授权
        """
        ensure_in_real_or_default_org()

        node_ids = set(node_ids)
        ancestor_node_keys = set()

        asset_perm_ids = set()

        nodes = PermNode.objects.filter(id__in=node_ids).only('id', 'key')
        for node in nodes:
            ancestor_node_keys.update(node.get_ancestor_keys())
        node_ids.update(
            PermNode.objects.filter(key__in=ancestor_node_keys).values_list('id', flat=True)
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
    def add_need_refresh_by_asset_perm_ids_cross_orgs(cls, asset_perm_ids):
        org_id_perm_ids_mapper = defaultdict(set)
        pairs = AssetPermission.objects.filter(id__in=asset_perm_ids).values_list('org_id', 'id')
        for org_id, perm_id in pairs:
            org_id_perm_ids_mapper[org_id].add(perm_id)
        for org_id, perm_ids in org_id_perm_ids_mapper.items():
            with tmp_to_org(org_id):
                cls.add_need_refresh_by_asset_perm_ids(perm_ids)

    @classmethod
    def add_need_refresh_by_asset_perm_ids(cls, asset_perm_ids):
        ensure_in_real_or_default_org()

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

    @timeit
    def refresh_if_need(self, force=False):
        user = self.user
        exists = UserAssetGrantedTreeNodeRelation.objects.filter(user=user).exists()

        if force or not exists:
            orgs = [*user.orgs.all(), Organization.default()]
        else:
            org_ids = self.get_and_delete_need_refresh_org_ids()
            orgs = [Organization.get_instance(org_id) for org_id in org_ids]

        for org in orgs:
            with tmp_to_org(org):
                utils = UserGrantedTreeBuildUtils(user)
                utils.rebuild_user_granted_tree()


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

    def get_direct_granted_nodes(self, node_only_fields=NODE_ONLY_FIELDS) -> NodeQuerySet:
        # 查询直接授权节点
        nodes = PermNode.objects.filter(
            granted_by_permissions__id__in=self.asset_perm_ids
        ).distinct().only(*node_only_fields)
        return nodes

    @property
    def direct_granted_asset_ids(self) -> list:
        asset_ids = Asset.org_objects.filter(
            granted_by_permissions__id__in=self.asset_perm_ids
        ).distinct().values_list('id', flat=True)
        asset_ids = list(asset_ids)
        return asset_ids

    @timeit
    def rebuild_user_granted_tree(self):
        ensure_in_real_or_default_org()

        user = self.user
        org_id = current_org.id

        with UserGrantedTreeRebuildLock(org_id, user.id):
            # 先删除旧的授权树🌲
            UserAssetGrantedTreeNodeRelation.objects.filter(
                user=user
            ).delete()

            if not self.asset_perm_ids:
                # 没有授权直接返回
                return

            nodes = self.compute_perm_nodes_tree()
            if not nodes:
                return
            self.create_mapping_nodes(nodes)
            self.compute_node_assets_amount_v2()

    def compute_perm_nodes_tree(self, node_only_fields=NODE_ONLY_FIELDS) -> list:

        # 查询直接授权节点
        nodes = self.get_direct_granted_nodes(node_only_fields=node_only_fields)

        # 授权的节点 key 集合
        granted_key_set = {_node.key for _node in nodes}

        def _has_ancestor_granted(node: PermNode):
            """
            判断一个节点是否有授权过的祖先节点
            """
            ancestor_keys = set(node.get_ancestor_keys())
            return ancestor_keys & granted_key_set

        key2leaf_nodes_mapper = {}

        # 给授权节点设置 is_granted 标识，同时去重
        for node in nodes:
            node: PermNode
            if _has_ancestor_granted(node):
                continue
            node.node_from = NodeFrom.granted
            key2leaf_nodes_mapper[node.key] = node

        # 查询授权资产关联的节点设置
        def process_direct_granted_assets():
            # 查询直接授权资产
            asset_ids = self.direct_granted_asset_ids
            # 查询授权资产关联的节点设置
            granted_asset_nodes = PermNode.objects.filter(
                assets__id__in=asset_ids
            ).distinct().only(*node_only_fields)

            # 给资产授权关联的节点设置 is_asset_granted 标识，同时去重
            for node in granted_asset_nodes:
                if _has_ancestor_granted(node):
                    continue
                if node.key in key2leaf_nodes_mapper:
                    continue
                node.node_from = NodeFrom.asset
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
        ancestors = PermNode.objects.filter(key__in=ancestor_keys).only(*node_only_fields)
        for node in ancestors:
            node.node_from = NodeFrom.child
        return [*leaf_nodes, *ancestors]

    def create_mapping_nodes(self, nodes, with_assets_amount=False):
        user = self.user
        to_create = []

        if with_assets_amount:
            def get_assets_amount(node):
                return node.assets_amount
        else:
            def get_assets_amount(node):
                return -1

        for node in nodes:
            to_create.append(UserAssetGrantedTreeNodeRelation(
                user=user,
                node=node,
                node_key=node.key,
                node_parent_key=node.parent_key,
                node_from=node.node_from,
                node_assets_amount=get_assets_amount(node),
                org_id=node.org_id
            ))

        UserAssetGrantedTreeNodeRelation.objects.bulk_create(to_create)

    @timeit
    def compute_node_assets_amount_v2(self):
        """
        可跨组织计算节点资产数量
        """
        granted_rel_nodes = UserAssetGrantedTreeNodeRelation.objects.filter(user=self.user)
        id_granted_rel_node_mapper = {n.id: n for n in granted_rel_nodes}

        tree = GrantedTree(granted_rel_nodes)
        tree.build_tree()

        for granted_rel_node in granted_rel_nodes:
            granted_rel_node: UserAssetGrantedTreeNodeRelation
            if granted_rel_node.node_from == NodeFrom.granted:
                continue
            else:
                granted_node, asset_granted_node = tree.get_node_descendant(
                    granted_rel_node.node_key, id_granted_rel_node_mapper
                )

                direct_ids = [n.node_id for n in granted_node]
                indirect_ids = [n.node_id for n in asset_granted_node]

                # 获取直接授权节点的所有子孙节点
                q = Q()
                for node in granted_node:
                    q |= Q(key__istartswith=f'{node.key}:')

                if q:
                    descendant_node_ids = PermNode.objects.order_by().filter(q).values_list('id', flat=True).distinct()
                    direct_ids.extend(descendant_node_ids)

                direct_granted_assets_qs = NodeAssetThrouth.objects.filter(
                    node_id__in=indirect_ids,
                    asset__assetpermission_id__in=self.asset_perm_ids
                ).values_list('asset_id')
                direct_granted_node_assets_qs = Asset.nodes.through.objects.filter(
                    node_id__in=direct_ids).values_list('asset_id').distinct()
                assets_qs = direct_granted_assets_qs.union(direct_granted_node_assets_qs)
                assets_amount = assets_qs.values_list('asset_id').distinct().count()
                granted_rel_node.node_assets_amount = assets_amount
        UserAssetGrantedTreeNodeRelation.objects.bulk_update(granted_rel_nodes, fields=('node_assets_amount',))

    @timeit
    def compute_node_assets_amount(self, nodes: List[PermNode]):
        """
        这里计算的是一个组织的
        """
        if len(nodes) == 1:
            node = nodes[0]
            if node.node_from == NodeFrom.granted and node.key.isdigit():
                # 直接授权了跟节点
                node.granted_assets_amount = node.assets_amount
                return

        asset_perm_ids = self.asset_perm_ids

        direct_granted_node_ids = [
            node.id for node in nodes
            if node.node_from == NodeFrom.granted
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
        node_only_fields = NODE_ONLY_FIELDS + ('value', 'full_value')
        nodes = self.compute_perm_nodes_tree(node_only_fields=node_only_fields)
        self.compute_node_assets_amount(nodes)

        # 查询直接授权节点的子节点
        q = Q()
        for node in self.get_direct_granted_nodes(node_only_fields=('key', )):
            q |= Q(key__startswith=f'{node.key}:')

        if q:
            descendant_nodes = PermNode.objects.filter(q).distinct()
        else:
            descendant_nodes = PermNode.objects.none()

        nodes.extend(descendant_nodes)
        return nodes


class UserGrantedAssetsQueryUtils(UserGrantedUtilsBase):

    def get_favorite_assets(self, qs_stage: QuerySetStage = None, only=('id', )) -> AssetQuerySet:
        favorite_asset_ids = FavoriteAsset.objects.filter(
            user=self.user).values_list('asset_id', flat=True)
        favorite_asset_ids = list(favorite_asset_ids)
        qs_stage = qs_stage or QuerySetStage()
        qs_stage.filter(id__in=favorite_asset_ids).only(*only)
        assets = self.get_all_granted_assets(qs_stage)
        return assets

    def get_ungroup_assets(self) -> AssetQuerySet:
        return self.get_direct_granted_assets()

    def get_direct_granted_assets(self) -> AssetQuerySet:
        queryset = Asset.org_objects.order_by().filter(
            granted_by_permissions__id__in=self.asset_perm_ids
        ).distinct()
        return queryset

    def get_direct_granted_nodes_assets(self, qs_stage: QuerySetStage = None) -> AssetQuerySet:
        granted_node_ids = AssetPermission.nodes.through.objects.filter(
            assetpermission_id__in=self.asset_perm_ids
        ).values_list('node_id', flat=True).distinct()
        granted_node_ids = list(granted_node_ids)
        granted_nodes = PermNode.objects.filter(id__in=granted_node_ids).only('id', 'key')
        queryset = PermNode.get_nodes_all_assets_v2(*granted_nodes)
        if qs_stage:
            queryset = qs_stage.merge(queryset)
        return queryset

    def get_all_granted_assets(self, qs_stage: QuerySetStage = None) -> AssetQuerySet:
        nodes_assets = self.get_direct_granted_nodes_assets()
        assets = self.get_direct_granted_assets()

        if qs_stage:
            nodes_assets, assets = qs_stage.merge_multi_before_union(nodes_assets, assets)
        queryset = nodes_assets.union(assets)
        if qs_stage:
            queryset = qs_stage.merge_after_union(queryset)
        return queryset

    def get_node_all_assets(self, id, qs_stage: QuerySetStage = None) -> Tuple[PermNode, AssetQuerySet]:
        node = PermNode.objects.get(id=id)
        granted_status = node.get_granted_status(self.user)
        if granted_status == NodeFrom.granted:
            assets = PermNode.get_nodes_all_assets_v2(node)
            if qs_stage:
                assets = qs_stage.merge(assets)
            return node, assets
        elif granted_status in (NodeFrom.asset, NodeFrom.child):
            node.use_granted_assets_amount()
            assets = self._get_indirect_granted_node_all_assets(node, qs_stage=qs_stage)
            return node, assets
        else:
            node.assets_amount = 0
            return node, Asset.org_objects.none()

    def get_node_assets(self, key) -> AssetQuerySet:
        node = PermNode.objects.get(key=key)
        granted_status = node.get_granted_status(self.user)

        if granted_status == NodeFrom.granted:
            assets = Asset.org_objects.order_by().filter(nodes_id=node.id)
            return assets
        elif granted_status == NodeFrom.asset:
            return self._get_indirect_granted_node_assets(node.id)
        else:
            return Asset.org_objects.none()

    def _get_indirect_granted_node_assets(self, id) -> AssetQuerySet:
        assets = Asset.org_objects.order_by().filter(nodes_id=id) & self.get_direct_granted_assets()
        return assets

    def _get_indirect_granted_node_all_assets(self, node, qs_stage: QuerySetStage = None) -> AssetQuerySet:
        """
        此算法依据 `UserGrantedMappingNode` 的数据查询
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
        node_assets = PermNode.get_nodes_all_assets_v2(*granted_nodes)

        # 查询该节点下的资产授权节点
        only_asset_granted_node_ids = UserAssetGrantedTreeNodeRelation.objects.filter(
            user=user, node_from=NodeFrom.asset
        ).filter(Q(node_key__startswith=f'{node.key}:')).values_list('node_id', flat=True)

        only_asset_granted_node_ids = list(only_asset_granted_node_ids)
        if node.node_from == NodeFrom.asset:
            only_asset_granted_node_ids.append(node.id)

        assets = Asset.org_objects.distinct().order_by().filter(
            nodes__id__in=only_asset_granted_node_ids,
            granted_by_permissions__id__in=self.asset_perm_ids
        )
        if qs_stage:
            node_assets, assets = qs_stage.merge_multi_before_union(node_assets, assets)
        granted_assets = node_assets.union(assets)
        granted_assets = qs_stage.merge_after_union(granted_assets)
        return granted_assets


class UserGrantedNodesQueryUtils(UserGrantedUtilsBase):
    def get_node_children(self, key):
        if not key:
            return self.get_top_level_nodes()

        node = PermNode.objects.get(key=key)
        granted_status = node.get_granted_status(self.user)
        if granted_status == NodeFrom.granted:
            return PermNode.objects.filter(parent_key=key)
        elif granted_status in (NodeFrom.asset, NodeFrom.child):
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
            granted_node_rels__user=user,
            parent_key=key
        ).annotate(
            **PermNode.annotate_granted_node_rel_fields
        ).distinct()

        # 设置节点授权资产数量
        for node in nodes:
            if not node.node_from == NodeFrom.granted:
                node.use_granted_assets_amount()
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

    @timeit
    def get_whole_tree_nodes(self, with_special=True):
        """
        这里的 granted nodes, 是整棵树需要的node，推算出来的也算
        :param user:
        :return:
        """
        # 获取 `UserGrantedMappingNode` 中对应的 `Node`
        nodes = PermNode.objects.filter(
            granted_node_rels__user=self.user
        ).annotate(
            **PermNode.annotate_granted_node_rel_fields
        ).distinct()

        key_to_node_mapper = {}
        nodes_descendant_q = Q()

        for node in nodes:
            if not node.is_granted:
                # 未授权的节点资产数量设置为 `UserGrantedMappingNode` 中的数量
                node.use_granted_assets_amount()
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
