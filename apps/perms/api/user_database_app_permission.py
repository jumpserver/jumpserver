# coding: utf-8
#

import uuid
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from common.permissions import IsOrgAdminOrAppUser, IsValidUser
from common.tree import TreeNodeSerializer
from orgs.mixins import generics
from users.models import User, UserGroup
from applications.serializers import DatabaseAppSerializer
from applications.models import DatabaseApp
from .. import utils

__all__ = [
    'UserGrantedDatabaseAppsApi',
    'UserGrantedDatabaseAppsAsTreeApi',
    'UserGroupGrantedDatabaseAppsApi',
    'ValidateUserDatabaseAppPermissionApi'
]


class UserGrantedDatabaseAppsApi(generics.ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = DatabaseAppSerializer
    filter_fields = ['id', 'name']
    search_fields = ['name']

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_queryset(self):
        util = utils.DatabaseAppPermissionUtil(self.get_object())
        queryset = util.get_database_apps()
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedDatabaseAppsAsTreeApi(UserGrantedDatabaseAppsApi):
    serializer_class = TreeNodeSerializer
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_serializer(self, database_apps, *args, **kwargs):
        if database_apps is None:
            database_apps = []
        only_database_app = self.request.query_params.get('only', '0') == '1'
        tree_root = None
        data = []
        if not only_database_app:
            tree_root = utils.construct_database_apps_tree_root()
            data.append(tree_root)
        for database_app in database_apps:
            node = utils.parse_database_app_to_tree_node(tree_root, database_app)
            data.append(node)
        data.sort()
        return super().get_serializer(data, many=True)


# Validate

class ValidateUserDatabaseAppPermissionApi(APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id', '')
        database_app_id = request.query_params.get('database_app_id', '')

        try:
            user_id = uuid.UUID(user_id)
            database_app_id = uuid.UUID(database_app_id)
        except ValueError:
            return Response({'msg': False}, status=403)

        user = get_object_or_404(User, id=user_id)
        database_app = get_object_or_404(DatabaseApp, id=database_app_id)

        util = utils.DatabaseAppPermissionUtil(user)
        database_apps = util.get_database_apps()
        if database_app in database_apps:
            return Response({'msg': True}, status=200)

        return Response({'msg': False}, status=403)


# UserGroup

class UserGroupGrantedDatabaseAppsApi(generics.ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = DatabaseAppSerializer

    def get_queryset(self):
        queryset = []
        user_group_id = self.kwargs.get('pk')
        if not user_group_id:
            return queryset
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        util = utils.DatabaseAppPermissionUtil(user_group)
        queryset = util.get_database_apps()
        return queryset
