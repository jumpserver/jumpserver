# coding:utf-8
from django.urls import path
from .. import views

app_name = 'applications'

urlpatterns = [
    # RemoteApp
    path('remote-app/', views.RemoteAppListView.as_view(), name='remote-app-list'),
    path('remote-app/create/', views.RemoteAppCreateView.as_view(), name='remote-app-create'),
    path('remote-app/<uuid:pk>/update/', views.RemoteAppUpdateView.as_view(), name='remote-app-update'),
    path('remote-app/<uuid:pk>/', views.RemoteAppDetailView.as_view(), name='remote-app-detail'),
    # User RemoteApp view
    path('user-remote-app/', views.UserRemoteAppListView.as_view(), name='user-remote-app-list')

]
