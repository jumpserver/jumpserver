import time
from collections import defaultdict

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from assets.models import Asset
from assets.utils import NodeAssetsUtil
from common.db.models import output_as_string
from common.decorators import on_transaction_commit, merge_delay_run
from common.utils import get_logger
from common.utils.common import lazyproperty, timeit
from orgs.models import Organization
from orgs.utils import (
    current_org,
    tmp_to_org,
    tmp_to_root_org
)
from perms.locks import UserGrantedTreeRebuildLock
from perms.models import (
    AssetPermission,
    UserAssetGrantedTreeNodeRelation,
    PermNode
)
from users.models import User
from . import UserPermAssetUtil
from .permission import AssetPermissionUtil

logger = get_logger(__name__)

__all__ = [
    'UserPermTreeRefreshUtil',
    'UserPermTreeExpireUtil'
]


class _UserPermTreeCacheMixin:
    """ 缓存数据 users: {org_id, org_id }, 记录用户授权树已经构建完成的组织集合 """
    cache_key_template = 'perms.user.node_tree.built_orgs.user_id:{user_id}'

    def get_cache_key(self, user_id):
        return self.cache_key_template.format(user_id=user_id)

    @lazyproperty
    def client(self):
        return cache.client.get_client(write=True)


class UserPermTreeRefreshUtil(_UserPermTreeCacheMixin):
    """ 用户授权树刷新工具, 针对某一个用户授权树的刷新 """

    def __init__(self, user):
        self.user = user

    @lazyproperty
    def orgs(self):
        return self.user.orgs.distinct()

    @lazyproperty
    def org_ids(self):
        return [str(o.id) for o in self.orgs]

    @lazyproperty
    def cache_key_user(self):
        return self.get_cache_key(self.user.id)

    @lazyproperty
    def cache_key_time(self):
        key = 'perms.user.node_tree.built_time.{}'.format(self.user.id)
        return key

    @timeit
    def refresh_if_need(self, force=False):
        built_just_now = False if settings.ASSET_SIZE == 'small' else cache.get(self.cache_key_time)
        if built_just_now:
            logger.info('Refresh user perm tree just now, pass: {}'.format(built_just_now))
            return
        to_refresh_orgs = self.orgs if force else self._get_user_need_refresh_orgs()
        if not to_refresh_orgs:
            logger.info('Not have to refresh orgs')
            return

        logger.info("Delay refresh user orgs: {} {}".format(self.user, [o.name for o in to_refresh_orgs]))
        sync = True if settings.ASSET_SIZE == 'small' else False
        refresh_user_orgs_perm_tree.apply(sync=sync, user_orgs=((self.user, tuple(to_refresh_orgs)),))
        refresh_user_favorite_assets.apply(sync=sync, users=(self.user,))

    @timeit
    def refresh_tree_manual(self):
        """
        用来手动 debug
        :return:
        """
        built_just_now = cache.get(self.cache_key_time)
        if built_just_now:
            logger.info('Refresh just now, pass: {}'.format(built_just_now))
            return
        to_refresh_orgs = self._get_user_need_refresh_orgs()
        if not to_refresh_orgs:
            logger.info('Not have to refresh orgs for user: {}'.format(self.user))
            return
        self.perform_refresh_user_tree(to_refresh_orgs)

    @timeit
    def perform_refresh_user_tree(self, to_refresh_orgs):
        # 再判断一次，毕竟构建树比较慢
        built_just_now = cache.get(self.cache_key_time)
        if built_just_now:
            logger.info('Refresh user perm tree just now, pass: {}'.format(built_just_now))
            return

        self._clean_user_perm_tree_for_legacy_org()
        if settings.ASSET_SIZE != 'small':
            ttl = settings.PERM_TREE_REGEN_INTERVAL
            cache.set(self.cache_key_time, int(time.time()), ttl)

        lock = UserGrantedTreeRebuildLock(self.user.id)
        got = lock.acquire(blocking=False)
        if not got:
            logger.info('User perm tree rebuild lock not acquired, pass')
            return

        try:
            for org in to_refresh_orgs:
                self._rebuild_user_perm_tree_for_org(org)
            self._mark_user_orgs_refresh_finished(to_refresh_orgs)
        finally:
            lock.release()

    def _rebuild_user_perm_tree_for_org(self, org):
        with tmp_to_org(org):
            start = time.time()
            UserPermTreeBuildUtil(self.user).rebuild_user_perm_tree()
            end = time.time()
            logger.info(
                'Refresh user perm tree: [{user}] org [{org}] {use_time:.2f}s'
                ''.format(user=self.user, org=org, use_time=end - start)
            )

    def _clean_user_perm_tree_for_legacy_org(self):
        with tmp_to_root_org():
            """ Clean user legacy org node relations """
            user_relations = UserAssetGrantedTreeNodeRelation.objects.filter(user=self.user)
            user_legacy_org_relations = user_relations.exclude(org_id__in=self.org_ids)
            user_legacy_org_relations.delete()

    def _get_user_need_refresh_orgs(self):
        cached_org_ids = self.client.smembers(self.cache_key_user)
        cached_org_ids = {oid.decode() for oid in cached_org_ids}
        to_refresh_org_ids = set(self.org_ids) - cached_org_ids
        to_refresh_orgs = list(Organization.objects.filter(id__in=to_refresh_org_ids))
        logger.info(f'Need to refresh orgs: {to_refresh_orgs}')
        return to_refresh_orgs

    def _mark_user_orgs_refresh_finished(self, orgs):
        org_ids = [str(org.id) for org in orgs]
        self.client.sadd(self.cache_key_user, *org_ids)


class UserPermTreeExpireUtil(_UserPermTreeCacheMixin):
    """ 用户授权树过期工具 """

    @lazyproperty
    def cache_key_all_user(self):
        return self.get_cache_key('*')

    def expire_perm_tree_for_nodes_assets(self, node_ids, asset_ids):
        node_perm_ids = AssetPermissionUtil().get_permissions_for_nodes(node_ids, flat=True)
        asset_perm_ids = AssetPermissionUtil().get_permissions_for_assets(asset_ids, flat=True)
        perm_ids = set(node_perm_ids) | set(asset_perm_ids)
        self.expire_perm_tree_for_perms(perm_ids)

    @tmp_to_root_org()
    def expire_perm_tree_for_perms(self, perm_ids):
        org_perm_ids = AssetPermission.objects.filter(id__in=perm_ids).values_list('org_id', 'id')
        org_perms_mapper = defaultdict(set)
        for org_id, perm_id in org_perm_ids:
            org_perms_mapper[org_id].add(perm_id)
        for org_id, perms_id in org_perms_mapper.items():
            user_ids = AssetPermission.get_all_users_for_perms(perm_ids, flat=True)
            self.expire_perm_tree_for_users_orgs(user_ids, [org_id])

    def expire_perm_tree_for_user_group(self, user_group):
        group_ids = [user_group.id]
        org_ids = [user_group.org_id]
        self.expire_perm_tree_for_user_groups_orgs(group_ids, org_ids)

    def expire_perm_tree_for_user_groups_orgs(self, group_ids, org_ids):
        user_ids = User.groups.through.objects \
            .filter(usergroup_id__in=group_ids) \
            .values_list('user_id', flat=True).distinct()
        self.expire_perm_tree_for_users_orgs(user_ids, org_ids)

    @on_transaction_commit
    def expire_perm_tree_for_users_orgs(self, user_ids, org_ids):
        user_ids = list(user_ids)
        org_ids = [str(oid) for oid in org_ids]
        with self.client.pipeline() as p:
            for uid in user_ids:
                cache_key = self.get_cache_key(uid)
                p.srem(cache_key, *org_ids)
            p.execute()
        users_display = ','.join([str(i) for i in user_ids[:3]])
        if len(user_ids) > 3:
            users_display += '...'
        orgs_display = ','.join([str(i) for i in org_ids[:3]])
        if len(org_ids) > 3:
            orgs_display += '...'
        logger.info('Expire perm tree for users: [{}], orgs: [{}]'.format(users_display, orgs_display))

    def expire_perm_tree_for_all_user(self):
        keys = self.client.keys(self.cache_key_all_user)
        with self.client.pipeline() as p:
            for k in keys:
                p.delete(k)
            p.execute()
        logger.info('Expire all user perm tree')


@merge_delay_run(ttl=20)
def refresh_user_orgs_perm_tree(user_orgs=()):
    for user, orgs in user_orgs:
        util = UserPermTreeRefreshUtil(user)
        util.perform_refresh_user_tree(orgs)


@merge_delay_run(ttl=20)
def refresh_user_favorite_assets(users=()):
    for user in users:
        util = UserPermAssetUtil(user)
        util.refresh_favorite_assets()
        util.refresh_type_nodes_tree_cache()


class UserPermTreeBuildUtil(object):
    node_only_fields = ('id', 'key', 'parent_key', 'org_id')

    def __init__(self, user):
        self.user = user
        self.user_perm_ids = AssetPermissionUtil().get_permissions_for_user(self.user, flat=True)
        # {key: node}
        self._perm_nodes_key_node_mapper = {}

    def rebuild_user_perm_tree(self):
        with transaction.atomic():
            self.clean_user_perm_tree()
            if not self.user_perm_ids:
                logger.info('User({}) not have permissions'.format(self.user))
                return
            self.compute_perm_nodes()
            self.compute_perm_nodes_asset_amount()
            self.create_mapping_nodes()

    def clean_user_perm_tree(self):
        UserAssetGrantedTreeNodeRelation.objects.filter(user=self.user).delete()

    def compute_perm_nodes(self):
        self._compute_perm_nodes_for_direct()
        self._compute_perm_nodes_for_direct_asset_if_need()
        self._compute_perm_nodes_for_ancestor()

    def compute_perm_nodes_asset_amount(self):
        """ 这里计算的是一个组织的授权树 """
        computed = self._only_compute_root_node_assets_amount_if_need()
        if computed:
            return

        nodekey_assetid_mapper = defaultdict(set)
        org_id = current_org.id
        for key in self.perm_node_keys_for_granted:
            asset_ids = PermNode.get_all_asset_ids_by_node_key(org_id, key)
            nodekey_assetid_mapper[key].update(asset_ids)

        for asset_id, node_id in self.direct_asset_id_node_id_pairs:
            node_key = self.perm_nodes_id_key_mapper.get(node_id)
            if not node_key:
                continue
            nodekey_assetid_mapper[node_key].add(asset_id)

        util = NodeAssetsUtil(self.perm_nodes, nodekey_assetid_mapper)
        util.generate()

        for node in self.perm_nodes:
            assets_amount = util.get_assets_amount(node.key)
            node.assets_amount = assets_amount

    def create_mapping_nodes(self):
        to_create = []
        for node in self.perm_nodes:
            relation = UserAssetGrantedTreeNodeRelation(
                user=self.user,
                node=node,
                node_key=node.key,
                node_parent_key=node.parent_key,
                node_from=node.node_from,
                node_assets_amount=node.assets_amount,
                org_id=node.org_id
            )
            to_create.append(relation)

        UserAssetGrantedTreeNodeRelation.objects.bulk_create(to_create)

    def _compute_perm_nodes_for_direct(self):
        """ 直接授权的节点（叶子节点）"""
        for node in self.direct_nodes:
            if self.has_any_ancestor_direct_permed(node):
                continue
            node.node_from = node.NodeFrom.granted
            self._perm_nodes_key_node_mapper[node.key] = node

    def _compute_perm_nodes_for_direct_asset_if_need(self):
        """ 直接授权的资产所在的节点（叶子节点）"""
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return
        for node in self.direct_asset_nodes:
            if self.has_any_ancestor_direct_permed(node):
                continue
            if node.key in self._perm_nodes_key_node_mapper:
                continue
            node.node_from = node.NodeFrom.asset
            self._perm_nodes_key_node_mapper[node.key] = node

    def _compute_perm_nodes_for_ancestor(self):
        """ 直接授权节点 和 直接授权资产所在节点 的所有祖先节点 (构造完整树) """
        ancestor_keys = set()
        for node in self._perm_nodes_key_node_mapper.values():
            ancestor_keys.update(node.get_ancestor_keys())
        ancestor_keys -= set(self._perm_nodes_key_node_mapper.keys())

        ancestors = PermNode.objects.filter(key__in=ancestor_keys).only(*self.node_only_fields)
        for node in ancestors:
            node.node_from = node.NodeFrom.child
            self._perm_nodes_key_node_mapper[node.key] = node

    @lazyproperty
    def perm_node_keys_for_granted(self):
        keys = [
            key for key, node in self._perm_nodes_key_node_mapper.items()
            if node.node_from == node.NodeFrom.granted
        ]
        return keys

    @lazyproperty
    def perm_nodes_id_key_mapper(self):
        mapper = {
            node.id.hex: node.key
            for key, node in self._perm_nodes_key_node_mapper.items()
        }
        return mapper

    def _only_compute_root_node_assets_amount_if_need(self):
        if len(self.perm_nodes) != 1:
            return False
        root_node = self.perm_nodes[0]
        if not root_node.is_org_root():
            return False
        if root_node.node_from != root_node.NodeFrom.granted:
            return False
        root_node.granted_assets_amount = len(root_node.get_all_asset_ids())
        return True

    @lazyproperty
    def perm_nodes(self):
        """ 授权树的所有节点 """
        return list(self._perm_nodes_key_node_mapper.values())

    def has_any_ancestor_direct_permed(self, node):
        """ 任何一个祖先节点被直接授权 """
        return bool(set(node.get_ancestor_keys()) & set(self.direct_node_keys))

    @lazyproperty
    def direct_node_keys(self):
        """ 直接授权的节点 keys """
        return {n.key for n in self.direct_nodes}

    @lazyproperty
    def direct_nodes(self):
        """ 直接授权的节点 """
        node_ids = AssetPermission.nodes.through.objects \
            .filter(assetpermission_id__in=self.user_perm_ids) \
            .values_list('node_id', flat=True).distinct()
        nodes = PermNode.objects.filter(id__in=node_ids).only(*self.node_only_fields)
        return nodes

    @lazyproperty
    def direct_asset_nodes(self):
        """ 获取直接授权的资产所在的节点 """
        node_ids = [node_id for asset_id, node_id in self.direct_asset_id_node_id_pairs]
        nodes = PermNode.objects.filter(id__in=node_ids).distinct().only(*self.node_only_fields)
        return nodes

    @lazyproperty
    def direct_asset_id_node_id_pairs(self):
        """ 直接授权的资产 id 和 节点 id  """
        asset_node_pairs = Asset.nodes.through.objects \
            .filter(asset_id__in=self.direct_asset_ids) \
            .annotate(
            str_asset_id=output_as_string('asset_id'),
            str_node_id=output_as_string('node_id')
        ).values_list('str_asset_id', 'str_node_id')
        asset_node_pairs = list(asset_node_pairs)
        return asset_node_pairs

    @lazyproperty
    def direct_asset_ids(self):
        """ 直接授权的资产 ids """
        asset_ids = AssetPermission.assets.through.objects \
            .filter(assetpermission_id__in=self.user_perm_ids) \
            .values_list('asset_id', flat=True) \
            .distinct()
        return asset_ids
