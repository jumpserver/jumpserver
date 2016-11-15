# coding:utf-8

from django.conf.urls import url
from rest_framework import routers
import views
import api

app_name = 'perms'

urlpatterns = [
    url(r'^asset-permission$', views.AssetPermissionListView.as_view(), name='asset-permission-list'),
    url(r'^asset-permission/create$', views.AssetPermissionCreateView.as_view(), name='asset-permission-create'),
    url(r'^asset-permission/(?P<pk>[0-9]+)/update$', views.AssetPermissionUpdateView.as_view(),
        name='asset-permission-update'),
    url(r'^asset-permission/(?P<pk>[0-9]+)$', views.AssetPermissionDetailView.as_view(),
        name='asset-permission-detail'),
    url(r'^asset-permission/(?P<pk>[0-9]+)/delete$', views.AssetPermissionDeleteView.as_view(),
        name='asset-permission-delete'),
    url(r'^asset-permission/(?P<pk>[0-9]+)/user$', views.AssetPermissionUserView.as_view(),
        name='asset-permission-user-list'),
    url(r'^asset-permission/(?P<pk>[0-9]+)/asset$', views.AssetPermissionAssetView.as_view(),
        name='asset-permission-asset-list'),
]

router = routers.DefaultRouter()
router.register('v1/asset-permissions', api.AssetPermissionViewSet, 'api-asset-permission')

urlpatterns += [
    url(r'^v1/user/my/assets/$', api.MyGrantedAssetsApi.as_view(), name='api-my-assets'),
    url(r'^v1/user/my/asset-groups/$', api.MyGrantedAssetsGroupsApi.as_view(), name='api-my-asset-groups'),
    url(r'^v1/user/my/asset-group/(?P<pk>[0-9]+)/assets/$', api.MyAssetGroupAssetsApi.as_view(),
        name='user-my-asset-group-assets'),

    # Select user permission of asset and asset group
    url(r'^v1/user/(?P<pk>[0-9]+)/assets/$', api.UserGrantedAssetsApi.as_view(), name='api-user-assets'),
    url(r'^v1/user/(?P<pk>[0-9]+)/asset-groups/$', api.UserGrantedAssetGroupsApi.as_view(),
        name='api-user-asset-groups'),

    # Select user group permission of asset and asset group
    url(r'^v1/user-group/(?P<pk>[0-9]+)/assets/$', api.UserGroupGrantedAssetsApi.as_view(), name='api-user-group-assets'),
    url(r'^v1/user-group/(?P<pk>[0-9]+)/asset-groups/$', api.UserGroupGrantedAssetGroupsApi.as_view(),
        name='api-user-group-asset-groups'),


    # Revoke permission api
    url(r'^v1/asset-permissions/user/revoke/', api.RevokeUserAssetPermission.as_view(),
        name='revoke-user-asset-permission'),
    url(r'^v1/asset-permissions/user-group/revoke/', api.RevokeUserGroupAssetPermission.as_view(),
        name='revoke-user-group-asset-permission'),
]

urlpatterns += router.urls
