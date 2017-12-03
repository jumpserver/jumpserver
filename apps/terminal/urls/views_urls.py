#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.conf.urls import url

from .. import views

app_name = 'terminal'

urlpatterns = [
    # Terminal view
    url(r'^terminal/$', views.TerminalListView.as_view(), name='terminal-list'),
    url(r'^terminal/(?P<pk>[0-9a-zA-Z\-]+)/$', views.TerminalDetailView.as_view(), name='terminal-detail'),
    url(r'^terminal/(?P<pk>[0-9a-zA-Z\-]+)/connect/$', views.TerminalConnectView.as_view(), name='terminal-connect'),
    url(r'^terminal/(?P<pk>[0-9a-zA-Z\-]+)/update/$', views.TerminalUpdateView.as_view(), name='terminal-update'),
    url(r'^(?P<pk>[0-9a-zA-Z\-]+)/accept/$', views.TerminalAcceptView.as_view(), name='terminal-accept'),

    # Session view
    url(r'^session/online/$', views.SessionOnlineListView.as_view(), name='session-online-list'),
    url(r'^session/offline$', views.SessionOfflineListView.as_view(), name='session-offline-list'),
    url(r'^session/(?P<pk>[0-9a-zA-Z\-]+)/$', views.SessionDetailView.as_view(), name='session-detail'),
]
