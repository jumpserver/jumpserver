#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.conf.urls import url

from .. import views

app_name = 'terminal'

urlpatterns = [
    url(r'^terminal/$', views.TerminalListView.as_view(), name='terminal-list'),
    url(r'^terminal/(?P<pk>[0-9a-zA-Z\-]+)/$', views.TerminalDetailView.as_view(),
        name='terminal-detail'),
    url(r'^terminal/(?P<pk>[0-9a-zA-Z\-]+)/connect/$', views.TerminalConnectView.as_view(),
        name='terminal-connect'),
    url(r'^terminal/(?P<pk>[0-9a-zA-Z\-]+)/update$', views.TerminalUpdateView.as_view(),
        name='terminal-update'),
    url(r'^terminal/(?P<pk>[0-9a-zA-Z\-]+)/modal/accept$', views.TerminalModelAccept.as_view(),
        name='terminal-modal-accept'),
]
