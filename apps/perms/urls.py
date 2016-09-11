# coding:utf-8

from django.conf.urls import url
import views

app_name = 'perms'

urlpatterns = [
    # Resource asset url
    url(r'^user$', views.PermUserAssetListView.as_view(), name='perm-user-list'),
    # url(r'^user/(?P<user>[0-9]+)/perm-asset/$', views.AssetListView.as_view(), name='perm-user-asset-list'),
    # url(r'^user/(?P<user>[0-9]+)/perm-asset/$', views.AssetListView.as_view(), name='perm-user-asset-list'),
    # url(r'^user/(?P<user>[0-9]+)$', views.AssetListView.as_view(), name='asset-list'),
    # url(r'^asset/create$', views.AssetCreateView.as_view(), name='asset-create'),
    # url(r'^asset/(?P<pk>[0-9]+)$', views.AssetDetailView.as_view(), name='asset-detail'),
    # url(r'^asset/(?P<pk>[0-9]+)/update', views.AssetUpdateView.as_view(), name='asset-update'),
    # url(r'^asset/(?P<pk>[0-9]+)/delete$', views.AssetDeleteView.as_view(), name='asset-delete'),
]

