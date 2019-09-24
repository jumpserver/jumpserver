# -*- coding: utf-8 -*-
#


from . import user_permission as uapi
from .mixin import UserGroupPermissionMixin

__all__ = [
    'UserGroupGrantedAssetsApi', 'UserGroupGrantedNodesApi',
    'UserGroupGrantedNodeAssetsApi', 'UserGroupGrantedNodeChildrenApi',
    'UserGroupGrantedNodeChildrenAsTreeApi',
    'UserGroupGrantedNodeChildrenWithAssetsAsTreeApi',
    'UserGroupGrantedAssetSystemUsersApi',
    # 'UserGroupGrantedNodeChildrenWithAssetsAsTreeApi',
]


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


class UserGroupGrantedNodeChildrenWithAssetsAsTreeApi(UserGroupPermissionMixin, uapi.UserGrantedNodeChildrenWithAssetsAsTreeApi):
    pass


class UserGroupGrantedAssetSystemUsersApi(UserGroupPermissionMixin, uapi.UserGrantedAssetSystemUsersApi):
    pass

