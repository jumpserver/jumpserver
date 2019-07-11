# -*- coding: utf-8 -*-

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from rest_framework.generics import (
    ListAPIView, get_object_or_404,
)
from rest_framework.pagination import LimitOffsetPagination

from common.permissions import IsValidUser, IsOrgAdminOrAppUser
from common.tree import TreeNodeSerializer
from ..utils import (
    RemoteAppPermissionUtil, construct_remote_apps_tree_root,
    parse_remote_app_to_tree_node,
)
from ..hands import User, RemoteApp, RemoteAppSerializer, UserGroup
from ..mixins import RemoteAppFilterMixin


__all__ = [
    'UserGrantedRemoteAppsApi', 'ValidateUserRemoteAppPermissionApi',
    'UserGrantedRemoteAppsAsTreeApi', 'UserGroupGrantedRemoteAppsApi',
]


class UserGrantedRemoteAppsApi(RemoteAppFilterMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = RemoteAppSerializer
    pagination_class = LimitOffsetPagination

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_queryset(self):
        util = RemoteAppPermissionUtil(self.get_object())
        queryset = util.get_remote_apps()
        queryset = list(queryset)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedRemoteAppsAsTreeApi(ListAPIView):
    serializer_class = TreeNodeSerializer
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if not user_id:
            user = self.request.user
        else:
            user = get_object_or_404(User, id=user_id)
        return user

    def get_queryset(self):
        queryset = []
        tree_root = construct_remote_apps_tree_root()
        queryset.append(tree_root)

        util = RemoteAppPermissionUtil(self.get_object())
        remote_apps = util.get_remote_apps()
        for remote_app in remote_apps:
            node = parse_remote_app_to_tree_node(tree_root, remote_app)
            queryset.append(node)

        queryset = sorted(queryset)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class ValidateUserRemoteAppPermissionApi(APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id', '')
        remote_app_id = request.query_params.get('remote_app_id', '')
        user = get_object_or_404(User, id=user_id)
        remote_app = get_object_or_404(RemoteApp, id=remote_app_id)

        util = RemoteAppPermissionUtil(user)
        remote_apps = util.get_remote_apps()
        if remote_app not in remote_apps:
            return Response({'msg': False}, status=403)
        return Response({'msg': True}, status=200)


# RemoteApp permission

class UserGroupGrantedRemoteAppsApi(ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser, )
    serializer_class = RemoteAppSerializer

    def get_queryset(self):
        queryset = []
        user_group_id = self.kwargs.get('pk')
        if not user_group_id:
            return queryset
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        util = RemoteAppPermissionUtil(user_group)
        queryset = util.get_remote_apps()
        return queryset
