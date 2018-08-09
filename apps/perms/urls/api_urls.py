# coding:utf-8

from django.urls import path
from rest_framework import routers
from .. import api

app_name = 'perms'

router = routers.DefaultRouter()
router.register('asset-permissions', api.AssetPermissionViewSet, 'asset-permission')

urlpatterns = [
    # 查询某个用户授权的资产和资产组
    path('user/<uuid:pk>/assets/',
         api.UserGrantedAssetsApi.as_view(), name='user-assets'),
    path('user/assets/', api.UserGrantedAssetsApi.as_view(),
         name='my-assets'),
    path('user/<uuid:pk>/nodes/',
         api.UserGrantedNodesApi.as_view(), name='user-nodes'),
    path('user/nodes/', api.UserGrantedNodesApi.as_view(),
         name='my-nodes'),
    path('user/<uuid:pk>/nodes/<uuid:node_id>/assets/',
         api.UserGrantedNodeAssetsApi.as_view(), name='user-node-assets'),
    path('user/nodes/<uuid:node_id>/assets/',
         api.UserGrantedNodeAssetsApi.as_view(), name='my-node-assets'),
    path('user/<uuid:pk>/nodes-assets/',
         api.UserGrantedNodesWithAssetsApi.as_view(), name='user-nodes-assets'),
    path('user/nodes-assets/', api.UserGrantedNodesWithAssetsApi.as_view(),
         name='my-nodes-assets'),

    # 查询某个用户组授权的资产和资产组
    path('user-group/<uuid:pk>/assets/',
         api.UserGroupGrantedAssetsApi.as_view(), name='user-group-assets'),
    path('user-group/<uuid:pk>/nodes/',
         api.UserGroupGrantedNodesApi.as_view(), name='user-group-nodes'),
    path('user-group/<uuid:pk>/nodes-assets/',
         api.UserGroupGrantedNodesWithAssetsApi.as_view(),
         name='user-group-nodes-assets'),
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
    path('asset-permission/user/validate/', api.ValidateUserAssetPermissionView.as_view(),
         name='validate-user-asset-permission'),
]

urlpatterns += router.urls

