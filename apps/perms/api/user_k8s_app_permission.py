# coding: utf-8
#

import uuid
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from common.permissions import IsOrgAdminOrAppUser, IsValidUser
from common.tree import TreeNodeSerializer
from orgs.mixins import generics
from users.models import User, UserGroup
from applications.serializers import K8sAppSerializer
from applications.models import K8sApp
from assets.models import SystemUser
from .. import utils, serializers
from .mixin import UserPermissionMixin


class UserGrantedK8sAppsApi(generics.ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = K8sAppSerializer
    filter_fields = ['id', 'name', 'type', 'comment']
    search_fields = ['name', 'comment']

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_queryset(self):
        util = utils.K8sAppPermissionUtil(self.get_object())
        queryset = util.get_k8s_apps()
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedK8sAppsAsTreeApi(UserGrantedK8sAppsApi):
    serializer_class = TreeNodeSerializer
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_serializer(self, k8s_apps, *args, **kwargs):
        if k8s_apps is None:
            k8s_apps = []
        only_k8s_app = self.request.query_params.get('only', '0') == '1'
        tree_root = None
        data = []
        if not only_k8s_app:
            tree_root = utils.construct_k8s_apps_tree_root()
            data.append(tree_root)
        for k8s_app in k8s_apps:
            node = utils.parse_k8s_app_to_tree_node(tree_root, k8s_app)
            data.append(node)
        data.sort()
        return super().get_serializer(data, many=True)


class UserGrantedK8sAppSystemUsersApi(UserPermissionMixin, generics.ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.K8sAppSystemUserSerializer
    only_fields = serializers.K8sAppSystemUserSerializer.Meta.only_fields

    def get_queryset(self):
        util = utils.K8sAppPermissionUtil(self.obj)
        k8s_app_id = self.kwargs.get('k8s_app_id')
        k8s_app = get_object_or_404(K8sApp, id=k8s_app_id)
        system_users = util.get_k8s_app_system_users(k8s_app)
        return system_users


# Validate

class ValidateUserK8sAppPermissionApi(APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id', '')
        k8s_app_id = request.query_params.get('k8s_app_id', '')
        system_user_id = request.query_params.get('system_user_id', '')

        try:
            user_id = uuid.UUID(user_id)
            k8s_app_id = uuid.UUID(k8s_app_id)
            system_user_id = uuid.UUID(system_user_id)
        except ValueError:
            return Response({'msg': False}, status=403)

        user = get_object_or_404(User, id=user_id)
        k8s_app = get_object_or_404(K8sApp, id=k8s_app_id)
        system_user = get_object_or_404(SystemUser, id=system_user_id)

        util = utils.K8sAppPermissionUtil(user)
        system_users = util.get_k8s_app_system_users(k8s_app)
        if system_user in system_users:
            return Response({'msg': True}, status=200)

        return Response({'msg': False}, status=403)


# UserGroup

class UserGroupGrantedK8sAppsApi(generics.ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = K8sAppSerializer

    def get_queryset(self):
        queryset = []
        user_group_id = self.kwargs.get('pk')
        if not user_group_id:
            return queryset
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        util = utils.K8sAppPermissionUtil(user_group)
        queryset = util.get_k8s_apps()
        return queryset
