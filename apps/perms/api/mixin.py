# -*- coding: utf-8 -*-
#
import uuid
from hashlib import md5
from django.core.cache import cache
from django.db.models import Q
from django.conf import settings
from rest_framework.views import Response
from django.utils.decorators import method_decorator
from django.views.decorators.http import condition

from django.utils.translation import ugettext as _
from common.utils import get_logger
from assets.utils import LabelFilterMixin
from ..utils import (
    AssetPermissionUtil
)
from .. import const
from ..hands import Asset, Node, SystemUser
from .. import serializers

logger = get_logger(__name__)

__all__ = ['UserPermissionCacheMixin', 'GrantAssetsMixin', 'NodesWithUngroupMixin']


def get_etag(request, *args, **kwargs):
    cache_policy = request.GET.get("cache_policy")
    if cache_policy != '1':
        return None
    if not UserPermissionCacheMixin.CACHE_ENABLE:
        return None
    view = request.parser_context.get("view")
    if not view:
        return None
    etag = view.get_meta_cache_id()
    return etag


class UserPermissionCacheMixin:
    cache_policy = '0'
    RESP_CACHE_KEY = '_PERMISSION_RESPONSE_CACHE_V2_{}'
    CACHE_ENABLE = settings.ASSETS_PERM_CACHE_ENABLE
    CACHE_TIME = settings.ASSETS_PERM_CACHE_TIME
    _object = None

    def get_object(self):
        return None

    # 内部使用可控制缓存
    def _get_object(self):
        if not self._object:
            self._object = self.get_object()
        return self._object

    def get_object_id(self):
        obj = self._get_object()
        if obj:
            return str(obj.id)
        return None

    def get_request_md5(self):
        path = self.request.path
        query = {k: v for k, v in self.request.GET.items()}
        query.pop("_", None)
        query = "&".join(["{}={}".format(k, v) for k, v in query.items()])
        full_path = "{}?{}".format(path, query)
        return md5(full_path.encode()).hexdigest()

    def get_meta_cache_id(self):
        obj = self._get_object()
        util = AssetPermissionUtil(obj, cache_policy=self.cache_policy)
        meta_cache_id = util.cache_meta.get('id')
        return meta_cache_id

    def get_response_cache_id(self):
        obj_id = self.get_object_id()
        request_md5 = self.get_request_md5()
        meta_cache_id = self.get_meta_cache_id()
        resp_cache_id = '{}_{}_{}'.format(obj_id, request_md5, meta_cache_id)
        return resp_cache_id

    def get_response_from_cache(self):
        # 没有数据缓冲
        meta_cache_id = self.get_meta_cache_id()
        if not meta_cache_id:
            logger.debug("Not get meta id: {}".format(meta_cache_id))
            return None
        # 从响应缓冲里获取响应
        key = self.get_response_key()
        data = cache.get(key)
        if not data:
            logger.debug("Not get response from cache: {}".format(key))
            return None
        logger.debug("Get user permission from cache: {}".format(self.get_object()))
        response = Response(data)
        return response

    def expire_response_cache(self):
        obj_id = self.get_object_id()
        expire_cache_id = '{}_{}'.format(obj_id, '*')
        key = self.RESP_CACHE_KEY.format(expire_cache_id)
        cache.delete_pattern(key)

    def get_response_key(self):
        resp_cache_id = self.get_response_cache_id()
        key = self.RESP_CACHE_KEY.format(resp_cache_id)
        return key

    def set_response_to_cache(self, response):
        key = self.get_response_key()
        cache.set(key, response.data, self.CACHE_TIME)
        logger.debug("Set response to cache: {}".format(key))

    @method_decorator(condition(etag_func=get_etag))
    def get(self, request, *args, **kwargs):
        if not self.CACHE_ENABLE:
            self.cache_policy = '0'
        else:
            self.cache_policy = request.GET.get('cache_policy', '0')

        obj = self._get_object()
        if obj is None:
            logger.debug("Not get response from cache: obj is none")
            return super().get(request, *args, **kwargs)

        if AssetPermissionUtil.is_not_using_cache(self.cache_policy):
            logger.debug("Not get resp from cache: {}".format(self.cache_policy))
            return super().get(request, *args, **kwargs)
        elif AssetPermissionUtil.is_refresh_cache(self.cache_policy):
            logger.debug("Not get resp from cache: {}".format(self.cache_policy))
            self.expire_response_cache()

        logger.debug("Try get response from cache")
        resp = self.get_response_from_cache()
        if not resp:
            resp = super().get(request, *args, **kwargs)
            self.set_response_to_cache(resp)
        return resp


class NodesWithUngroupMixin:
    util = None

    @staticmethod
    def get_ungrouped_node(ungroup_key):
        return Node(key=ungroup_key, id=const.UNGROUPED_NODE_ID,
                    value=_("ungrouped"))

    @staticmethod
    def get_empty_node():
        return Node(key=const.EMPTY_NODE_KEY, id=const.EMPTY_NODE_ID,
                    value=_("empty"))

    def add_ungrouped_nodes(self, node_map, node_keys):
        ungroup_key = '1:-1'
        for key in node_keys:
            if key.endswith('-1'):
                ungroup_key = key
                break
        ungroup_node = self.get_ungrouped_node(ungroup_key)
        empty_node = self.get_empty_node()
        node_map[ungroup_key] = ungroup_node
        node_map[const.EMPTY_NODE_KEY] = empty_node


class GrantAssetsMixin(LabelFilterMixin):
    serializer_class = serializers.AssetGrantedSerializer

    def get_serializer_queryset(self, queryset):
        assets_ids = []
        system_users_ids = set()
        for asset in queryset:
            assets_ids.append(asset["id"])
            system_users_ids.update(set(asset["system_users"]))
        assets = Asset.objects.filter(id__in=assets_ids).only(
            *self.serializer_class.Meta.only_fields
        )
        assets_map = {asset.id: asset for asset in assets}
        system_users = SystemUser.objects.filter(id__in=system_users_ids).only(
            *self.serializer_class.system_users_only_fields
        )
        system_users_map = {s.id: s for s in system_users}
        data = []
        for item in queryset:
            i = item["id"]
            asset = assets_map.get(i)
            if not asset:
                continue

            _system_users = item["system_users"]
            system_users_granted = []
            for sid, action in _system_users.items():
                system_user = system_users_map.get(sid)
                if not system_user:
                    continue
                if not asset.has_protocol(system_user.protocol):
                    continue
                system_user.actions = action
                system_users_granted.append(system_user)
            asset.system_users_granted = system_users_granted
            data.append(asset)
        return data

    def get_serializer(self, queryset_list, many=True):
        data = self.get_serializer_queryset(queryset_list)
        return super().get_serializer(data, many=True)

    def filter_queryset_by_id(self, assets_items):
        i = self.request.query_params.get("id")
        if not i:
            return assets_items
        try:
            pk = uuid.UUID(i)
        except ValueError:
            return assets_items
        assets_map = {asset['id']: asset for asset in assets_items}
        if pk in assets_map:
            return [assets_map.get(pk)]
        else:
            return []

    def search_queryset(self, assets_items):
        search = self.request.query_params.get("search")
        if not search:
            return assets_items
        assets_map = {asset['id']: asset for asset in assets_items}
        assets_ids = set(assets_map.keys())
        assets_ids_search = Asset.objects.filter(id__in=assets_ids).filter(
            Q(hostname__icontains=search) | Q(ip__icontains=search)
        ).values_list('id', flat=True)
        return [assets_map.get(asset_id) for asset_id in assets_ids_search]

    def filter_queryset_by_label(self, assets_items):
        labels_id = self.get_filter_labels_ids()
        if not labels_id:
            return assets_items

        assets_map = {asset['id']: asset for asset in assets_items}
        assets_matched = Asset.objects.filter(id__in=assets_map.keys())
        for label_id in labels_id:
            assets_matched = assets_matched.filter(labels=label_id)
        assets_ids_matched = assets_matched.values_list('id', flat=True)
        return [assets_map.get(asset_id) for asset_id in assets_ids_matched]

    def sort_queryset(self, assets_items):
        order_by = self.request.query_params.get('order', 'hostname')

        if order_by not in ['hostname', '-hostname', 'ip', '-ip']:
            order_by = 'hostname'
        assets_map = {asset['id']: asset for asset in assets_items}
        assets_ids_search = Asset.objects.filter(id__in=assets_map.keys())\
            .order_by(order_by)\
            .values_list('id', flat=True)
        return [assets_map.get(asset_id) for asset_id in assets_ids_search]

    def filter_queryset(self, assets_items):
        assets_items = self.filter_queryset_by_id(assets_items)
        assets_items = self.search_queryset(assets_items)
        assets_items = self.filter_queryset_by_label(assets_items)
        assets_items = self.sort_queryset(assets_items)
        return assets_items
