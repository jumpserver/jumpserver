# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404

from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser
from ..hands import UserGroup
from .. import serializers

from .user_permission import (
    UserGrantedAssetsApi, UserGrantedNodesApi, UserGrantedNodesWithAssetsApi,
    UserGrantedNodesWithAssetsAsTreeApi, UserGrantedNodeAssetsApi,
    UserGrantedNodesAsTreeApi,
)

__all__ = [
    'UserGroupGrantedAssetsApi', 'UserGroupGrantedNodesApi',
    'UserGroupGrantedNodesWithAssetsApi', 'UserGroupGrantedNodeAssetsApi',
    'UserGroupGrantedNodesWithAssetsAsTreeApi', 'UserGroupGrantedNodesAsTreeApi',
]


class UserGroupGrantedAssetsApi(UserGrantedAssetsApi):
    def get_object(self):
        user_group_id = self.kwargs.get('pk', '')
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        return user_group


class UserGroupGrantedNodesApi(UserGrantedNodesApi):
    def get_object(self):
        user_group_id = self.kwargs.get('pk', '')
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        return user_group


class UserGroupGrantedNodesAsTreeApi(UserGrantedNodesAsTreeApi):
    def get_object(self):
        user_group_id = self.kwargs.get('pk', '')
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        return user_group


class UserGroupGrantedNodesWithAssetsApi(UserGrantedNodesWithAssetsApi):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.NodeGrantedSerializer

    def get_object(self):
        user_group_id = self.kwargs.get('pk', '')
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        return user_group


class UserGroupGrantedNodesWithAssetsAsTreeApi(UserGrantedNodesWithAssetsAsTreeApi):
    def get_object(self):
        user_group_id = self.kwargs.get('pk', '')
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        return user_group


class UserGroupGrantedNodeAssetsApi(UserGrantedNodeAssetsApi):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetGrantedSerializer

    def get_object(self):
        user_group_id = self.kwargs.get('pk', '')
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        return user_group
