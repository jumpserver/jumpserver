import time
from collections import defaultdict

from django.core.cache import cache

from common.decorator import on_transaction_commit
from common.utils import get_logger
from common.utils.common import lazyproperty, timeit
from orgs.models import Organization
from orgs.utils import (
    tmp_to_org,
    tmp_to_root_org
)
from perms.locks import UserGrantedTreeRebuildLock
from perms.models import (
    AssetPermission,
    UserAssetGrantedTreeNodeRelation
)
from perms.utils.user_permission import UserGrantedTreeBuildUtils
from users.models import User
from .permission import AssetPermissionUtil

logger = get_logger(__name__)

__all__ = ['UserPermTreeRefreshUtil', 'UserPermTreeExpireUtil']


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
        self.orgs = self.user.orgs.distinct()
        self.org_ids = [str(o.id) for o in self.orgs]

    @lazyproperty
    def cache_key_user(self):
        return self.get_cache_key(self.user.id)

    @timeit
    def refresh_if_need(self, force=False):
        self.clean_user_perm_tree_nodes_for_legacy_org()
        to_refresh_orgs = self.orgs if force else self.get_user_need_refresh_orgs()
        if not to_refresh_orgs:
            logger.info('Not have to refresh orgs')
            return
        with UserGrantedTreeRebuildLock(self.user.id):
            for org in to_refresh_orgs:
                self.rebuild_user_perm_tree_for_org(org)
        self.mark_user_orgs_refresh_finished(to_refresh_orgs)

    def rebuild_user_perm_tree_for_org(self, org):
        with tmp_to_org(org):
            start = time.time()
            UserGrantedTreeBuildUtils(self.user).rebuild_user_granted_tree()
            end = time.time()
            logger.info(
                'Refresh user [{user}] org [{org}] perm tree, user {use_time:.2f}s'
                ''.format(user=self.user, org=org, use_time=end - start)
            )

    def clean_user_perm_tree_nodes_for_legacy_org(self):
        with tmp_to_root_org():
            """ Clean user legacy org node relations """
            user_relations = UserAssetGrantedTreeNodeRelation.objects.filter(user=self.user)
            user_legacy_org_relations = user_relations.exclude(org_id__in=self.org_ids)
            user_legacy_org_relations.delete()

    def get_user_need_refresh_orgs(self):
        cached_org_ids = self.client.smembers(self.cache_key_user)
        cached_org_ids = {oid.decode() for oid in cached_org_ids}
        to_refresh_org_ids = set(self.org_ids) - cached_org_ids
        to_refresh_orgs = Organization.objects.filter(id__in=to_refresh_org_ids)
        logger.info(f'Need to refresh orgs: {to_refresh_orgs}')
        return to_refresh_orgs

    def mark_user_orgs_refresh_finished(self, org_ids):
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
            org_ids = [org_id]
            user_ids = AssetPermission.get_all_users_for_perms(perm_ids, flat=True)
            self.expire_perm_tree_for_users_orgs(user_ids, org_ids)

    def expire_perm_tree_for_user_group(self, user_group):
        group_ids = [user_group.id]
        org_ids = [user_group.org_id]
        self.expire_perm_tree_for_user_groups_orgs(group_ids, org_ids)

    def expire_perm_tree_for_user_groups_orgs(self, group_ids, org_ids):
        user_ids = User.groups.through.objects.filter(usergroup_id__in=group_ids) \
            .values_list('user_id', flat=True).distinct()
        self.expire_perm_tree_for_users_orgs(user_ids, org_ids)

    @on_transaction_commit
    def expire_perm_tree_for_users_orgs(self, user_ids, org_ids):
        org_ids = [str(oid) for oid in org_ids]
        with self.client.pipline() as p:
            for uid in user_ids:
                cache_key = self.get_cache_key(uid)
                p.srem(cache_key, *org_ids)
            p.execute()
        logger.info('Expire perm tree for users: [{}], orgs: [{}]'.format(user_ids, org_ids))

    def expire_perm_tree_for_all_user(self):
        keys = self.client.keys(self.cache_key_all_user)
        with self.client.pipline() as p:
            for k in keys:
                p.delete(k)
            p.execute()
        logger.info('Expire all user perm tree')
