# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404

from ..hands import UserGroup

from . import user_permission as uapi

__all__ = [
    'UserGroupGrantedAssetsApi', 'UserGroupGrantedNodesApi',
    'UserGroupGrantedNodeAssetsApi', 'UserGroupGrantedNodeChildrenApi',
    'UserGroupGrantedNodeChildrenAsTreeApi', 'UserGroupGrantedNodesWithAssetsAsTreeApi',
    'UserGroupGrantedAssetSystemUsersApi',
    # 'UserGroupGrantedNodesWithAssetsAsTreeApi',
]


class UserGroupPermissionMixin:
    obj = None

    def get_object(self):
        user_group_id = self.kwargs.get('pk', '')
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        return user_group


class UserGroupGrantedAssetsApi(UserGroupPermissionMixin, uapi.UserGrantedAssetsApi):
    pass


class UserGroupGrantedNodeAssetsApi(UserGroupPermissionMixin, uapi.UserGrantedNodeAssetsApi):
    pass


class UserGroupGrantedNodesApi(UserGroupPermissionMixin, uapi.UserGrantedNodesApi):
    pass


class UserGroupGrantedNodeChildrenApi(UserGroupPermissionMixin, uapi.UserGrantedNodeChildrenApi):
    pass


class UserGroupGrantedNodeChildrenAsTreeApi(UserGroupPermissionMixin, uapi.UserGrantedNodeChildrenAsTreeApi):
    pass


class UserGroupGrantedNodesWithAssetsAsTreeApi(UserGroupPermissionMixin, uapi.UserGrantedNodesWithAssetsAsTreeApi):
    pass


class UserGroupGrantedAssetSystemUsersApi(UserGroupPermissionMixin, uapi.UserGrantedAssetSystemUsersApi):
    pass

