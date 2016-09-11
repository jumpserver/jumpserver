# coding:utf-8

from django.conf.urls import url
import views

app_name = 'perms'

urlpatterns = [
    url(r'^asset-permission$', views.UserAssetPermissionListView.as_view(), name='asset-permission-list'),
    url(r'^asset-permission/create$', views.UserAssetPermissionCreateView.as_view(), name='asset-permission-create'),
]

