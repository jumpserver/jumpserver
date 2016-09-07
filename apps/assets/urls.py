# coding:utf-8
from django.conf.urls import url, include
import views
# from .api import (
#     AssetGroupViewSet, AssetViewSet, IDCViewSet
# )
# from rest_framework import routers
# router = routers.DefaultRouter()
# router.register(r'assetgroup', AssetGroupViewSet)
# router.register(r'asset', AssetViewSet)
# router.register(r'idc', IDCViewSet)
app_name = 'assets'

urlpatterns = [
    url(r'^$', views.AssetListView.as_view(), name='asset-index'),
    url(r'^asset$', views.AssetListView.as_view(), name='asset-list'),
    url(r'^asset/create$', views.AssetCreateView.as_view(), name='asset-create'),
    url(r'^asset/(?P<pk>[0-9]+)$', views.AssetDetailView.as_view(), name='asset-detail'),
    url(r'^asset/(?P<pk>[0-9]+)/update', views.AssetUpdateView.as_view(), name='asset-update'),
    url(r'^asset/(?P<pk>[0-9]+)/delete$', views.AssetDeleteView.as_view(), name='asset-delete'),
    url(r'^asset-group$', views.AssetGroupListView.as_view(), name='asset-group-list'),
    url(r'^asset-group/create$', views.AssetGroupCreateView.as_view(), name='asset-group-create'),
    url(r'^asset-group/(?P<pk>[0-9]+)$', views.AssetGroupDetailView.as_view(), name='asset-group-detail'),
    url(r'^asset-group/(?P<pk>[0-9]+)/update$', views.AssetGroupUpdateView.as_view(), name='asset-group-update'),
    url(r'^asset-group/(?P<pk>[0-9]+)/delete$', views.AssetGroupDeleteView.as_view(), name='asset-group-delete'),
    url(r'^idc$', views.IDCListView.as_view(), name='idc-list'),
    url(r'^idc/create$', views.IDCCreateView.as_view(), name='idc-create'),
    url(r'^idc/(?P<pk>[0-9]+)$', views.IDCDetailView.as_view(), name='idc-detail'),
    url(r'^idc/(?P<pk>[0-9]+)/update', views.IDCUpdateView.as_view(), name='idc-update'),
    url(r'^idc/(?P<pk>[0-9]+)/delete$', views.IDCDeleteView.as_view(), name='idc-delete'),
    # url(r'^api/v1.0/', include(router.urls)),
]
