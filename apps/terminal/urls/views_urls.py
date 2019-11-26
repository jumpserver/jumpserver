#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.urls import path

from .. import views

app_name = 'terminal'

urlpatterns = [
    # Terminal view
    path('terminal/', views.TerminalListView.as_view(), name='terminal-list'),
    path('terminal/<uuid:pk>/', views.TerminalDetailView.as_view(), name='terminal-detail'),
    path('terminal/<uuid:pk>/connect/', views.TerminalConnectView.as_view(), name='terminal-connect'),
    path('terminal/<uuid:pk>/update/', views.TerminalUpdateView.as_view(), name='terminal-update'),
    path('<uuid:pk>/accept/', views.TerminalAcceptView.as_view(), name='terminal-accept'),
    path('web-terminal/', views.WebTerminalView.as_view(), name='web-terminal'),
    path('web-sftp/', views.WebSFTPView.as_view(), name='web-sftp'),

    # Session view
    path('session-online/', views.SessionOnlineListView.as_view(), name='session-online-list'),
    path('session-offline/', views.SessionOfflineListView.as_view(), name='session-offline-list'),
    path('session/<uuid:pk>/', views.SessionDetailView.as_view(), name='session-detail'),

    # Command view
    path('command/', views.CommandListView.as_view(), name='command-list'),

    # replay-storage
    path('terminal/replay-storage/', views.ReplayStorageListView.as_view(), name='replay-storage-list'),
    path('terminal/replay-storage/create/', views.ReplayStorageCreateView.as_view(), name='replay-storage-create'),
    path('terminal/replay-storage/<uuid:pk>/update/', views.ReplayStorageUpdateView.as_view(), name='replay-storage-update'),

    # command-storage
    path('terminal/command-storage/', views.CommandStorageListView.as_view(), name='command-storage-list'),
    path('terminal/command-storage/create/', views.CommandStorageCreateView.as_view(), name='command-storage-create'),
    path('terminal/command-storage/<uuid:pk>/update/', views.CommandStorageUpdateView.as_view(), name='command-storage-update'),

]
