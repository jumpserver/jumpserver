# coding:utf-8
from django.conf.urls import url
from .views import *

app_name = 'assets'

urlpatterns = [
    url(r'^add/$', AssetAddView.as_view(), name='asset-add'),
    url(r'^$', AssetListView.as_view(), name='asset-list'),
    url(r'^(?P<pk>[0-9]+)/delete/$', AssetDeleteView.as_view(), name='asset-list'),
    url(r'^(?P<pk>[0-9]+)/detail/$', AssetDetailView.as_view(), name='asset-detail'),
]
