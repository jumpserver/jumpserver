# coding:utf-8

from django.conf.urls import url
from rest_framework import routers
from .. import api

app_name = 'perms'

router = routers.DefaultRouter()
router.register('v1/asset-permissions', api.AssetPermissionViewSet, 'asset-permission')

urlpatterns = [
    # 查询某个用户授权的资产和资产组
    url(r'^v1/user/(?P<pk>[0-9a-zA-Z\-]{36})?/?assets/$', api.UserGrantedAssetsApi.as_view(), name='user-assets'),
    url(r'^v1/user/(?P<pk>[0-9a-zA-Z\-]{36})?/?nodes/$', api.UserGrantedNodesWithAssetsApi.as_view(), name='user-nodes'),

    # 查询某个用户组授权的资产和资产组
    url(r'^v1/user-group/(?P<pk>[0-9a-zA-Z\-]{36})/assets/$', api.UserGroupGrantedAssetsApi.as_view(), name='user-group-assets'),
    url(r'^v1/user-group/(?P<pk>[0-9a-zA-Z\-]{36})/nodes/$', api.UserGroupGrantedNodeApi.as_view(), name='user-group-asset-groups'),

    # 验证用户是否有某个资产和系统用户的权限
    url(r'v1/asset-permission/user/validate/$', api.ValidateUserAssetPermissionView.as_view(), name='validate-user-asset-permission'),
]

urlpatterns += router.urls

