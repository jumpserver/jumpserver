# coding:utf-8

from django.conf.urls import url
from django.urls import path
from .. import views

app_name = 'perms'

urlpatterns = [
    path('asset-permission/', views.AssetPermissionListView.as_view(), name='asset-permission-list'),
    path('asset-permission/create/', views.AssetPermissionCreateView.as_view(), name='asset-permission-create'),
    path('asset-permission/<uuid:pk>/update/', views.AssetPermissionUpdateView.as_view(), name='asset-permission-update'),
    path('asset-permission/<uuid:pk>/', views.AssetPermissionDetailView.as_view(),name='asset-permission-detail'),
    path('asset-permission/<uuid:pk>/delete/', views.AssetPermissionDeleteView.as_view(), name='asset-permission-delete'),
    path('asset-permission/<uuid:pk>/user/', views.AssetPermissionUserView.as_view(), name='asset-permission-user-list'),
    path('asset-permission/<uuid:pk>/asset/', views.AssetPermissionAssetView.as_view(), name='asset-permission-asset-list'),
]
