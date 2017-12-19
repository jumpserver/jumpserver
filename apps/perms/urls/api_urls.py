# coding:utf-8

from django.conf.urls import url
from rest_framework import routers
from .. import api

app_name = 'perms'

router = routers.DefaultRouter()
router.register('v1/asset-permissions',
                api.AssetPermissionViewSet,
                'asset-permission')

urlpatterns = [
    # 用户可以使用自己的Token或其它认证查看自己授权的资产,资产组等
    url(r'^v1/user/my/assets/$', api.MyGrantedAssetsApi.as_view(), name='my-assets'),
    url(r'^v1/user/my/asset-groups/$', api.MyGrantedAssetGroupsApi.as_view(), name='my-asset-groups'),
    url(r'^v1/user/my/asset-groups-assets/$', api.MyGrantedAssetGroupsWithAssetsApi.as_view(), name='my-asset-group-assets'),
    url(r'^v1/user/my/asset-group/(?P<pk>[0-9a-zA-Z\-]{36})/assets/$', api.MyAssetGroupOfAssetsApi.as_view(), name='my-asset-group-of-assets'),

    # 查询某个用户授权的资产和资产组
    url(r'^v1/user/(?P<pk>[0-9a-zA-Z\-]{36})/assets/$', api.UserGrantedAssetsApi.as_view(), name='user-assets'),
    url(r'^v1/user/(?P<pk>[0-9a-zA-Z\-]{36})/asset-groups/$', api.UserGrantedAssetGroupsApi.as_view(), name='user-asset-groups'),
    url(r'^v1/user/(?P<pk>[0-9a-zA-Z\-]{36})/asset-groups-assets/$', api.UserGrantedAssetGroupsWithAssetsApi.as_view(), name='user-asset-groups'),

    # 查询某个用户组授权的资产和资产组
    url(r'^v1/user-group/(?P<pk>[0-9a-zA-Z\-]{36})/assets/$', api.UserGroupGrantedAssetsApi.as_view(), name='user-group-assets'),
    url(r'^v1/user-group/(?P<pk>[0-9a-zA-Z\-]{36})/asset-groups/$', api.UserGroupGrantedAssetGroupsApi.as_view(), name='user-group-asset-groups'),

    # 用户和资产授权变更
    url(r'^v1/asset-permissions/(?P<pk>[0-9a-zA-Z\-]{36})/user/remove/$', api.AssetPermissionRemoveUserApi.as_view(), name='asset-permission-remove-user'),
    url(r'^v1/asset-permissions/(?P<pk>[0-9a-zA-Z\-]{36})/user/add/$', api.AssetPermissionAddUserApi.as_view(), name='asset-permission-add-user'),
    url(r'^v1/asset-permissions/(?P<pk>[0-9a-zA-Z\-]{36})/asset/remove/$', api.AssetPermissionRemoveAssetApi.as_view(), name='asset-permission-remove-asset'),
    url(r'^v1/asset-permissions/(?P<pk>[0-9a-zA-Z\-]{36})/asset/add/$', api.AssetPermissionAddAssetApi.as_view(), name='asset-permission-add-asset'),

    # 验证用户是否有某个资产和系统用户的权限
    url(r'v1/asset-permission/user/validate/$', api.ValidateUserAssetPermissionView.as_view(), name='validate-user-asset-permission'),
]

urlpatterns += router.urls

