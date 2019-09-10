# -*- coding: utf-8 -*-

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from rest_framework.generics import (
    ListAPIView, get_object_or_404,
)

from common.permissions import IsValidUser, IsOrgAdminOrAppUser
from common.tree import TreeNodeSerializer
from ..utils import (
    RemoteAppPermissionUtil, construct_remote_apps_tree_root,
    parse_remote_app_to_tree_node,
)
from ..hands import User, RemoteAppSerializer, UserGroup
from ..mixins import RemoteAppFilterMixin


__all__ = [
    'UserGrantedRemoteAppsApi', 'ValidateUserRemoteAppPermissionApi',
    'UserGrantedRemoteAppsAsTreeApi', 'UserGroupGrantedRemoteAppsApi',
]


class UserGrantedRemoteAppsApi(RemoteAppFilterMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = RemoteAppSerializer
    filter_fields = ['id']

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
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedRemoteAppsAsTreeApi(UserGrantedRemoteAppsApi):
    serializer_class = TreeNodeSerializer
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_serializer(self, *args, **kwargs):
        only_remote_app = self.request.query_params.get('only', '0') == '1'
        tree_root = None
        data = []
        if not only_remote_app:
            tree_root = construct_remote_apps_tree_root()
            data.append(tree_root)
        queryset = super().get_queryset()
        for remote_app in queryset:
            node = parse_remote_app_to_tree_node(tree_root, remote_app)
            data.append(node)
        data.sort()
        return super().get_serializer(data, many=True)


class ValidateUserRemoteAppPermissionApi(APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id', '')
        remote_app_id = request.query_params.get('remote_app_id', '')

        user = get_object_or_404(User, id=user_id)
        util = RemoteAppPermissionUtil(user)
        remote_app = util.get_remote_apps().filter(id=remote_app_id).exists()
        if remote_app:
            return Response({'msg': True}, status=200)
        return Response({'msg': False}, status=403)


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
