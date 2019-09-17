# -*- coding: utf-8 -*-
#
import uuid
from django.db.models import Q

from rest_framework.generics import get_object_or_404
from assets.utils import LabelFilterMixin
from common.permissions import IsValidUser, IsOrgAdminOrAppUser
from common.utils import get_logger
from orgs.utils import set_to_root_org
from ..hands import User, UserGroup, Asset, SystemUser
from .. import serializers


logger = get_logger(__name__)

__all__ = [
    'UserPermissionMixin', 'UserGroupPermissionMixin',
]


class UserPermissionMixin:
    permission_classes = (IsOrgAdminOrAppUser,)
    obj = None

    def initial(self, *args, **kwargs):
        super().initial(*args, *kwargs)
        self.obj = self.get_obj()

    def get(self, request, *args, **kwargs):
        set_to_root_org()
        return super().get(request, *args, **kwargs)

    def get_obj(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGroupPermissionMixin:
    obj = None

    def get_obj(self):
        user_group_id = self.kwargs.get('pk', '')
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        return user_group


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

    def get_serializer(self, assets_items=None, many=True):
        if assets_items is None:
            assets_items = []
        assets_items = self.get_serializer_queryset(assets_items)
        return super().get_serializer(assets_items, many=many)

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
