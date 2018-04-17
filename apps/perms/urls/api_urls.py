# coding:utf-8

from django.conf.urls import url
from rest_framework import routers
from .. import api

app_name = 'perms'

router = routers.DefaultRouter()
router.register('v1/asset-permissions', api.AssetPermissionViewSet, 'asset-permission')

urlpatterns = [
    # 查询某个用户授权的资产和资产组
    url(r'^v1/user/(?P<pk>[0-9a-zA-Z\-]{36})/assets/$',
        api.UserGrantedAssetsApi.as_view(), name='user-assets'),
    url(r'^v1/user/assets/$', api.UserGrantedAssetsApi.as_view(),
        name='my-assets'),
    url(r'^v1/user/(?P<pk>[0-9a-zA-Z\-]{36})/nodes/$',
        api.UserGrantedNodesApi.as_view(), name='user-nodes'),
    url(r'^v1/user/nodes/$', api.UserGrantedNodesApi.as_view(),
        name='my-nodes'),
    url(
        r'^v1/user/(?P<pk>[0-9a-zA-Z\-]{36})/nodes/(?P<node_id>[0-9a-zA-Z\-]{36})/assets/$',
        api.UserGrantedNodeAssetsApi.as_view(), name='user-node-assets'),
    url(r'^v1/user/nodes/(?P<node_id>[0-9a-zA-Z\-]{36})/assets/$',
        api.UserGrantedNodeAssetsApi.as_view(), name='my-node-assets'),
    url(r'^v1/user/(?P<pk>[0-9a-zA-Z\-]{36})/nodes-assets/$',
        api.UserGrantedNodesWithAssetsApi.as_view(), name='user-nodes-assets'),
    url(r'^v1/user/nodes-assets/$', api.UserGrantedNodesWithAssetsApi.as_view(),
        name='my-nodes-assets'),

    # 查询某个用户组授权的资产和资产组
    url(r'^v1/user-group/(?P<pk>[0-9a-zA-Z\-]{36})/assets/$',
        api.UserGroupGrantedAssetsApi.as_view(), name='user-group-assets'),
    url(r'^v1/user-group/(?P<pk>[0-9a-zA-Z\-]{36})/nodes/$',
        api.UserGroupGrantedNodesApi.as_view(), name='user-group-nodes'),
    url(r'^v1/user-group/(?P<pk>[0-9a-zA-Z\-]{36})/nodes-assets/$',
        api.UserGroupGrantedNodesWithAssetsApi.as_view(),
        name='user-group-nodes-assets'),
    url(
        r'^v1/user-group/(?P<pk>[0-9a-zA-Z\-]{36})/nodes/(?P<node_id>[0-9a-zA-Z\-]{36})/assets/$',
        api.UserGroupGrantedNodeAssetsApi.as_view(),
        name='user-group-node-assets'),

    # 用户和资产授权变更
    url(r'^v1/asset-permissions/(?P<pk>[0-9a-zA-Z\-]{36})/user/remove/$',
        api.AssetPermissionRemoveUserApi.as_view(),
        name='asset-permission-remove-user'),
    url(r'^v1/asset-permissions/(?P<pk>[0-9a-zA-Z\-]{36})/user/add/$',
        api.AssetPermissionAddUserApi.as_view(),
        name='asset-permission-add-user'),
    url(r'^v1/asset-permissions/(?P<pk>[0-9a-zA-Z\-]{36})/asset/remove/$',
        api.AssetPermissionRemoveAssetApi.as_view(),
        name='asset-permission-remove-asset'),
    url(r'^v1/asset-permissions/(?P<pk>[0-9a-zA-Z\-]{36})/asset/add/$',
        api.AssetPermissionAddAssetApi.as_view(),
        name='asset-permission-add-asset'),

    # 验证用户是否有某个资产和系统用户的权限
    url(r'v1/asset-permission/user/validate/$', api.ValidateUserAssetPermissionView.as_view(), name='validate-user-asset-permission'),
]

urlpatterns += router.urls

