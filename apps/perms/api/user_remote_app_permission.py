# -*- coding: utf-8 -*-

import uuid
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response

from common.permissions import IsValidUser, IsOrgAdminOrAppUser
from common.tree import TreeNodeSerializer
from orgs.mixins import generics
from ..utils import (
    RemoteAppPermissionUtil, construct_remote_apps_tree_root,
    parse_remote_app_to_tree_node,
)
from ..hands import User, RemoteApp, RemoteAppSerializer, UserGroup, SystemUser
from .mixin import UserPermissionMixin
from .. import serializers


__all__ = [
    'UserGrantedRemoteAppsApi', 'ValidateUserRemoteAppPermissionApi',
    'UserGrantedRemoteAppsAsTreeApi', 'UserGroupGrantedRemoteAppsApi',
    'UserGrantedRemoteAppSystemUsersApi',
]


class UserGrantedRemoteAppsApi(generics.ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = RemoteAppSerializer
    filter_fields = ['name', 'id']
    search_fields = ['name']

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

    def get_serializer(self, remote_apps=None, *args, **kwargs):
        if remote_apps is None:
            remote_apps = []
        only_remote_app = self.request.query_params.get('only', '0') == '1'
        tree_root = None
        data = []
        if not only_remote_app:
            tree_root = construct_remote_apps_tree_root()
            data.append(tree_root)
        for remote_app in remote_apps:
            node = parse_remote_app_to_tree_node(tree_root, remote_app)
            data.append(node)
        data.sort()
        return super().get_serializer(data, many=True)


class UserGrantedRemoteAppSystemUsersApi(UserPermissionMixin, generics.ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.RemoteAppSystemUserSerializer
    only_fields = serializers.RemoteAppSystemUserSerializer.Meta.only_fields

    def get_queryset(self):
        util = RemoteAppPermissionUtil(self.obj)
        remote_app_id = self.kwargs.get('remote_app_id')
        remote_app = get_object_or_404(RemoteApp, id=remote_app_id)
        system_users = util.get_remote_app_system_users(remote_app)
        return system_users


class ValidateUserRemoteAppPermissionApi(APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id', '')
        remote_app_id = request.query_params.get('remote_app_id', '')
        system_id = request.query_params.get('system_user_id', '')

        try:
            user_id = uuid.UUID(user_id)
            remote_app_id = uuid.UUID(remote_app_id)
            system_id = uuid.UUID(system_id)
        except ValueError:
            return Response({'msg': False}, status=403)

        user = get_object_or_404(User, id=user_id)
        remote_app = get_object_or_404(RemoteApp, id=remote_app_id)
        system_user = get_object_or_404(SystemUser, id=system_id)

        util = RemoteAppPermissionUtil(user)
        system_users = util.get_remote_app_system_users(remote_app)
        if system_user in system_users:
            return Response({'msg': True}, status=200)

        return Response({'msg': False}, status=403)


# RemoteApp permission

class UserGroupGrantedRemoteAppsApi(generics.ListAPIView):
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
