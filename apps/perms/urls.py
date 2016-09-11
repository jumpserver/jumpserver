# coding:utf-8

from django.conf.urls import url
import views

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
]

