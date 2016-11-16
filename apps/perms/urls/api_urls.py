# coding:utf-8

from django.conf.urls import url
from rest_framework import routers
from .. import api

app_name = 'perms'

router = routers.DefaultRouter()
router.register('v1/asset-permissions', api.AssetPermissionViewSet, 'asset-permission')

urlpatterns = [
    url(r'^v1/user/my/assets/$', api.MyGrantedAssetsApi.as_view(), name='my-assets'),
    url(r'^v1/user/my/asset-groups/$', api.MyGrantedAssetsGroupsApi.as_view(), name='my-asset-groups'),
    url(r'^v1/user/my/asset-group/(?P<pk>[0-9]+)/assets/$', api.MyAssetGroupAssetsApi.as_view(),
        name='user-my-asset-group-assets'),

    # Select user permission of asset and asset group
    url(r'^v1/user/(?P<pk>[0-9]+)/assets/$', api.UserGrantedAssetsApi.as_view(), name='user-assets'),
    url(r'^v1/user/(?P<pk>[0-9]+)/asset-groups/$', api.UserGrantedAssetGroupsApi.as_view(),
        name='user-asset-groups'),

    # Select user group permission of asset and asset group
    url(r'^v1/user-group/(?P<pk>[0-9]+)/assets/$', api.UserGroupGrantedAssetsApi.as_view(), name='user-group-assets'),
    url(r'^v1/user-group/(?P<pk>[0-9]+)/asset-groups/$', api.UserGroupGrantedAssetGroupsApi.as_view(),
        name='user-group-asset-groups'),


    # Revoke permission api
    url(r'^v1/asset-permissions/user/revoke/', api.RevokeUserAssetPermission.as_view(),
        name='revoke-user-asset-permission'),
    url(r'^v1/asset-permissions/user-group/revoke/', api.RevokeUserGroupAssetPermission.as_view(),
        name='revoke-user-group-asset-permission'),
]

urlpatterns += router.urls

