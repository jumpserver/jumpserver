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
    url(r'^asset/add$', views.AssetAddView.as_view(), name='asset-add'),
    url(r'^asset/(?P<pk>[0-9]+)$', views.AssetDetailView.as_view(), name='asset-detail'),
    url(r'^asset/(?P<pk>[0-9]+)$/edit', views.AssetEditView.as_view(), name='asset-edit'),
    url(r'^asset/(?P<pk>[0-9]+)/delete$', views.AssetDeleteView.as_view(), name='asset-delete'),
    url(r'^assetgroup$', views.AssetGroupListView.as_view(), name='assetgroup-list'),
    url(r'^assetgroup/add$', views.AssetGroupAddView.as_view(), name='assetgroup-add'),
    url(r'^assetgroup/(?P<pk>[0-9]+)$', views.AssetGroupDetailView.as_view(), name='assetgroup-detail'),
    url(r'^assetgroup/(?P<pk>[0-9]+)/edit$', views.AssetGroupEditView.as_view(), name='assetgroup-edit'),
    url(r'^assetgroup/(?P<pk>[0-9]+)/delete$', views.AssetGroupDeleteView.as_view(), name='assetgroup-delete'),
    # url(r'^api/v1.0/', include(router.urls)),
]
