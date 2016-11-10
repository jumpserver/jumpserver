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
    url(r'^v1/user/assets/$', api.UserAssetsApi.as_view(), name='api-user-assets'),
    url(r'^v1/asset-permissions/user/revoke/', api.RevokeUserAssetPermission.as_view(),
        name='revoke-user-asset-permission'),
    url(r'^v1/user/asset-groups/$', api.UserAssetsGroupsApi.as_view(), name='api-user-asset-groups'),
    url(r'^v1/user/asset-group/(?P<pk>[0-9]+)/assets/$', api.UserAssetsGroupAssetsApi.as_view(),
        name='user-asset-groups-assets'),
]

urlpatterns += router.urls
