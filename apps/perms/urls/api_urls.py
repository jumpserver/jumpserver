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
    url(r'^v1/user/my/assets/$',
        api.MyGrantedAssetsApi.as_view(),
        name='my-assets'),
    url(r'^v1/user/my/asset-groups/$',
        api.MyGrantedAssetsGroupsApi.as_view(),
        name='my-asset-groups'),
    url(r'^v1/user/my/asset-groups-assets/$',
        api.MyAssetGroupAssetsApi.as_view(),
        name='my-asset-group-assets'),
    url(r'^v1/user/my/asset-group/(?P<pk>[0-9]+)/assets/$',
        api.MyAssetGroupOfAssetsApi.as_view(),
        name='my-asset-group-of-assets'),

    # 查询某个用户授权的资产和资产组
    url(r'^v1/user/(?P<pk>[0-9]+)/assets/$',
        api.UserGrantedAssetsApi.as_view(),
        name='user-assets'),
    url(r'^v1/user/(?P<pk>[0-9]+)/asset-groups/$',
        api.UserGrantedAssetGroupsApi.as_view(),
        name='user-asset-groups'),

    # 查询某个用户组授权的资产和资产组
    url(r'^v1/user-group/(?P<pk>[0-9]+)/assets/$',
        api.UserGroupGrantedAssetsApi.as_view(),
        name='user-group-assets'),
    url(r'^v1/user-group/(?P<pk>[0-9]+)/asset-groups/$',
        api.UserGroupGrantedAssetGroupsApi.as_view(),
        name='user-group-asset-groups'),

    # 回收用户或用户组授权
    url(r'^v1/asset-permissions/user/revoke/$',
        api.RevokeUserAssetPermission.as_view(),
        name='revoke-user-asset-permission'),
    url(r'^v1/asset-permissions/user-group/revoke/$',
        api.RevokeUserGroupAssetPermission.as_view(),
        name='revoke-user-group-asset-permission'),

    # 验证用户是否有某个资产和系统用户的权限
    url(r'v1/asset-permission/user/validate/$',
        api.ValidateUserAssetPermissionView.as_view(),
        name='validate-user-asset-permission'),

    # 删除asset permission中的某个系统用户
    url(r'^v1/asset-permissions/(?P<pk>[0-9]+)/system-user/remove/$',
        api.RemoveSystemUserAssetPermission.as_view(),
        name='remove-system-user-asset-permission'),
]

urlpatterns += router.urls

