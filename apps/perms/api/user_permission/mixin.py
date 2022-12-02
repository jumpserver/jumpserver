# -*- coding: utf-8 -*-
#
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from rest_framework.request import Request
from rest_framework.response import Response

from assets.api.asset.asset import AssetFilterSet
from assets.api.mixin import SerializeToTreeNodeMixin
from common.exceptions import JMSObjectDoesNotExist
from common.http import is_true
from common.utils import is_uuid
from perms import serializers
from perms.utils.user_permission import UserGrantedTreeRefreshController
from rbac.permissions import RBACPermission
from users.models import User


class RebuildTreeMixin:
    user: User

    def get(self, request: Request, *args, **kwargs):
        force = is_true(request.query_params.get('rebuild_tree'))
        controller = UserGrantedTreeRefreshController(self.user)
        controller.refresh_if_need(force)
        return super().get(request, *args, **kwargs)


class SelfOrPKUserMixin:
    kwargs: dict
    request: Request
    permission_classes = (RBACPermission,)

    def get_rbac_perms(self):
        if self.request_user_is_self():
            return self.self_rbac_perms
        else:
            return self.admin_rbac_perms

    @property
    def self_rbac_perms(self):
        return (
            ('list', 'perms.view_myassets'),
            ('retrieve', 'perms.view_myassets'),
            ('get_tree', 'perms.view_myassets'),
            ('GET', 'perms.view_myassets'),
            ('OPTIONS', 'perms.view_myassets'),
        )

    @property
    def admin_rbac_perms(self):
        return (
            ('list', 'perms.view_userassets'),
            ('retrieve', 'perms.view_userassets'),
            ('get_tree', 'perms.view_userassets'),
            ('GET', 'perms.view_userassets'),
            ('OPTIONS', 'perms.view_userassets'),
        )

    @property
    def user(self):
        if self.request_user_is_self():
            user = self.request.user
        elif is_uuid(self.kwargs.get('user')):
            user = get_object_or_404(User, pk=self.kwargs.get('user'))
        elif hasattr(self, 'swagger_fake_view'):
            user = self.request.user
        else:
            raise JMSObjectDoesNotExist(object_name=_('User'))
        return user

    def request_user_is_self(self):
        return self.kwargs.get('user') in ['my', 'self']


class PermedAssetSerializerMixin:
    serializer_class = serializers.AssetGrantedSerializer
    filterset_class = AssetFilterSet
    search_fields = ['name', 'address', 'comment']
    ordering_fields = ("name", "address")
    ordering = ('name',)


class AssetsTreeFormatMixin(SerializeToTreeNodeMixin):
    """
    将 资产 序列化成树的结构返回
    """
    filter_queryset: callable
    get_queryset: callable

    filterset_fields = ['name', 'address', 'id', 'comment']
    search_fields = ['name', 'address', 'comment']

    def list(self, request: Request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if request.query_params.get('search'):
            # 如果用户搜索的条件不精准，会导致返回大量的无意义数据。
            # 这里限制一下返回数据的最大条数
            queryset = queryset[:999]
            queryset = sorted(queryset, key=lambda asset: asset.name)
        data = self.serialize_assets(queryset, None)
        return Response(data=data)
