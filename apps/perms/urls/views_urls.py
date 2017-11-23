# coding:utf-8

from django.conf.urls import url
from .. import views

app_name = 'perms'

urlpatterns = [
    url(r'^asset-permission$', views.AssetPermissionListView.as_view(), name='asset-permission-list'),
    url(r'^asset-permission/create$', views.AssetPermissionCreateView.as_view(), name='asset-permission-create'),
    url(r'^asset-permission/(?P<pk>[0-9a-zA-Z\-]+)/update$', views.AssetPermissionUpdateView.as_view(), name='asset-permission-update'),
    url(r'^asset-permission/(?P<pk>[0-9a-zA-Z\-]+)$', views.AssetPermissionDetailView.as_view(),name='asset-permission-detail'),
    url(r'^asset-permission/(?P<pk>[0-9a-zA-Z\-]+)/delete$', views.AssetPermissionDeleteView.as_view(), name='asset-permission-delete'),
    url(r'^asset-permission/(?P<pk>[0-9a-zA-Z\-]+)/user$', views.AssetPermissionUserView.as_view(), name='asset-permission-user-list'),
    url(r'^asset-permission/(?P<pk>[0-9a-zA-Z\-]+)/asset$', views.AssetPermissionAssetView.as_view(), name='asset-permission-asset-list'),
]


