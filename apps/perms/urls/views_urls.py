# coding:utf-8

from django.conf.urls import url
from django.urls import path
from .. import views

app_name = 'perms'

urlpatterns = [
    # asset-permission
    path('asset-permission/', views.AssetPermissionListView.as_view(), name='asset-permission-list'),
    path('asset-permission/create/', views.AssetPermissionCreateView.as_view(), name='asset-permission-create'),
    path('asset-permission/<uuid:pk>/update/', views.AssetPermissionUpdateView.as_view(), name='asset-permission-update'),
    path('asset-permission/<uuid:pk>/', views.AssetPermissionDetailView.as_view(),name='asset-permission-detail'),
    path('asset-permission/<uuid:pk>/delete/', views.AssetPermissionDeleteView.as_view(), name='asset-permission-delete'),
    path('asset-permission/<uuid:pk>/user/', views.AssetPermissionUserView.as_view(), name='asset-permission-user-list'),
    path('asset-permission/<uuid:pk>/asset/', views.AssetPermissionAssetView.as_view(), name='asset-permission-asset-list'),

    # remote-app-permission
    path('remote-app-permission/', views.RemoteAppPermissionListView.as_view(), name='remote-app-permission-list'),
    path('remote-app-permission/create/', views.RemoteAppPermissionCreateView.as_view(), name='remote-app-permission-create'),
    path('remote-app-permission/<uuid:pk>/update/', views.RemoteAppPermissionUpdateView.as_view(), name='remote-app-permission-update'),
    path('remote-app-permission/<uuid:pk>/', views.RemoteAppPermissionDetailView.as_view(), name='remote-app-permission-detail'),
    path('remote-app-permission/<uuid:pk>/user/', views.RemoteAppPermissionUserView.as_view(), name='remote-app-permission-user-list'),
    path('remote-app-permission/<uuid:pk>/remote-app/', views.RemoteAppPermissionRemoteAppView.as_view(), name='remote-app-permission-remote-app-list'),
]
