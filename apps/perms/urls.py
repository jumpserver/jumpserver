# coding:utf-8

from django.conf.urls import url
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

urlpatterns += [
    url(r'^v1/asset-permission/$', api.AssetPermissionListCreateApi.as_view(),
        name='asset-permission-list-create-api'),
    url(r'^v1/user/assets/$', api.UserAssetsApi.as_view(),
        name='user-assets'),
    url(r'^v1/user/asset-groups/$', api.UserAssetsGroupsApi.as_view(),
        name='user-asset-groups'),
    url(r'^v1/user/asset-groups/(?P<pk>[0-9]+)/assets/$', api.UserAssetsGroupAssetsApi.as_view(),
        name='user-asset-groups-assets'),
]

