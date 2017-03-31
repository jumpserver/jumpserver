#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.conf.urls import url

from .. import views

app_name = 'applications'

urlpatterns = [
    url(r'^terminal/$', views.TerminalListView.as_view(), name='terminal-list'),
    url(r'^terminal/(?P<pk>\d+)/$', views.TerminalDetailView.as_view(),
        name='terminal-detail'),
    url(r'^terminal/(?P<pk>\d+)/connect/$', views.TerminalConnectView.as_view(),
        name='terminal-connect'),
    url(r'^terminal/(?P<pk>\d+)/update$', views.TerminalUpdateView.as_view(),
        name='terminal-update'),
    url(r'^terminal/(?P<pk>\d+)/modal/accept$', views.TerminalModelAccept.as_view(),
        name='terminal-modal-accept'),
]
