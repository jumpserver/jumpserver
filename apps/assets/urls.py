# coding:utf-8
from django.conf.urls import url, include
from .views import *
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
    url(r'^assets/add/$', AssetAddView.as_view(), name='asset-add'),
    url(r'^$', AssetListView.as_view(), name='asset-list'),
    url(r'^(?P<pk>[0-9]+)/delete/$', AssetDeleteView.as_view(), name='asset-delete'),
    url(r'^(?P<pk>[0-9]+)/detail/$', AssetDetailView.as_view(), name='asset-detail'),
    # url(r'^api/v1.0/', include(router.urls)),
]
