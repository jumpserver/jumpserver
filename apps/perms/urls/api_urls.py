# coding:utf-8

from django.urls import path
from rest_framework import routers
from .. import api

app_name = 'perms'

router = routers.DefaultRouter()
router.register('actions', api.ActionViewSet, 'action')
router.register('asset-permissions', api.AssetPermissionViewSet, 'asset-permission')
router.register('remote-app-permissions', api.RemoteAppPermissionViewSet, 'remote-app-permission')

asset_permission_urlpatterns = [
    # 查询某个用户授权的资产和资产组
    path('user/<uuid:pk>/assets/',
         api.UserGrantedAssetsApi.as_view(), name='user-assets'),
    path('user/assets/', api.UserGrantedAssetsApi.as_view(),
         name='my-assets'),
    path('user/<uuid:pk>/nodes/',
         api.UserGrantedNodesApi.as_view(), name='user-nodes'),
    path('user/nodes/', api.UserGrantedNodesApi.as_view(),
         name='my-nodes'),
    path('user/nodes/children/', api.UserGrantedNodeChildrenApi.as_view(),
         name='my-node-children'),
    path('user/<uuid:pk>/nodes/<uuid:node_id>/assets/',
         api.UserGrantedNodeAssetsApi.as_view(), name='user-node-assets'),
    path('user/nodes/<uuid:node_id>/assets/',
         api.UserGrantedNodeAssetsApi.as_view(), name='my-node-assets'),
    path('user/<uuid:pk>/nodes-assets/',
         api.UserGrantedNodesWithAssetsApi.as_view(), name='user-nodes-assets'),
    path('user/nodes-assets/', api.UserGrantedNodesWithAssetsApi.as_view(),
         name='my-nodes-assets'),
    path('user/<uuid:pk>/nodes-assets/tree/',
         api.UserGrantedNodesWithAssetsAsTreeApi.as_view(), name='user-nodes-assets-as-tree'),
    path('user/nodes-assets/tree/', api.UserGrantedNodesWithAssetsAsTreeApi.as_view(),
         name='my-nodes-assets-as-tree'),

    # 查询某个用户组授权的资产和资产组
    path('user-group/<uuid:pk>/assets/',
         api.UserGroupGrantedAssetsApi.as_view(), name='user-group-assets'),
    path('user-group/<uuid:pk>/nodes/',
         api.UserGroupGrantedNodesApi.as_view(), name='user-group-nodes'),
    path('user-group/<uuid:pk>/nodes-assets/',
         api.UserGroupGrantedNodesWithAssetsApi.as_view(),
         name='user-group-nodes-assets'),
    path('user-group/<uuid:pk>/nodes-assets/tree/',
         api.UserGroupGrantedNodesWithAssetsAsTreeApi.as_view(),
         name='user-group-nodes-assets-as-tree'),
    path('user-group/<uuid:pk>/nodes/<uuid:node_id>/assets/',
         api.UserGroupGrantedNodeAssetsApi.as_view(),
         name='user-group-node-assets'),

    # 用户和资产授权变更
    path('asset-permissions/<uuid:pk>/user/remove/',
         api.AssetPermissionRemoveUserApi.as_view(),
         name='asset-permission-remove-user'),
    path('asset-permissions/<uuid:pk>/user/add/',
         api.AssetPermissionAddUserApi.as_view(),
         name='asset-permission-add-user'),
    path('asset-permissions/<uuid:pk>/asset/remove/',
         api.AssetPermissionRemoveAssetApi.as_view(),
         name='asset-permission-remove-asset'),
    path('asset-permissions/<uuid:pk>/asset/add/',
         api.AssetPermissionAddAssetApi.as_view(),
         name='asset-permission-add-asset'),

    # 验证用户是否有某个资产和系统用户的权限
    path('asset-permission/user/validate/', api.ValidateUserAssetPermissionApi.as_view(),
         name='validate-user-asset-permission'),
    path('asset-permission/user/actions/', api.GetUserAssetPermissionActionsApi.as_view(),
         name='get-user-asset-permission-actions'),
]


remote_app_permission_urlpatterns = [
    # 查询用户授权的RemoteApp
    path('user/<uuid:pk>/remote-apps/',
         api.UserGrantedRemoteAppsApi.as_view(), name='user-remote-apps'),
    path('user/remote-apps/',
         api.UserGrantedRemoteAppsApi.as_view(), name='my-remote-apps'),

    # 获取用户授权的RemoteApp树
    path('user/<uuid:pk>/remote-apps/tree/',
         api.UserGrantedRemoteAppsAsTreeApi.as_view(),
         name='user-remote-apps-as-tree'),
    path('user/remote-apps/tree/',
         api.UserGrantedRemoteAppsAsTreeApi.as_view(),
         name='my-remote-apps-as-tree'),

    # 查询用户组授权的RemoteApp
    path('user-group/<uuid:pk>/remote-apps/',
         api.UserGroupGrantedRemoteAppsApi.as_view(),
         name='user-group-remote-apps'),

    # 校验用户对RemoteApp的权限
    path('remote-app-permission/user/validate/',
         api.ValidateUserRemoteAppPermissionApi.as_view(),
         name='validate-user-remote-app-permission'),

    # 用户和RemoteApp变更
    path('remote-app-permissions/<uuid:pk>/user/add/',
         api.RemoteAppPermissionAddUserApi.as_view(),
         name='remote-app-permission-add-user'),
    path('remote-app-permissions/<uuid:pk>/user/remove/',
         api.RemoteAppPermissionRemoveUserApi.as_view(),
         name='remote-app-permission-remove-user'),
    path('remote-app-permissions/<uuid:pk>/remote-app/remove/',
         api.RemoteAppPermissionRemoveRemoteAppApi.as_view(),
         name='remote-app-permission-remove-remote-app'),
    path('remote-app-permissions/<uuid:pk>/remote-app/add/',
         api.RemoteAppPermissionAddRemoteAppApi.as_view(),
         name='remote-app-permission-add-remote-app'),
]

urlpatterns = asset_permission_urlpatterns + remote_app_permission_urlpatterns

urlpatterns += router.urls

