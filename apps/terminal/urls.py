#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

from django.conf.urls import url

import views
import api

app_name = 'terminal'

urlpatterns = [
    url(r'^terminal$', views.TerminalListView.as_view(), name='terminal-list'),
    url(r'^terminal/(?P<pk>\d+)/update$', views.TerminalUpdateView.as_view(), name='terminal-update'),
]

urlpatterns += [
    url(r'^v1/terminal/$', api.TerminalCreateListApi.as_view(), name='terminal-list-create-api'),
    url(r'^v1/terminal/(?P<pk>\d+)/$', api.TerminalApiDetailUpdateDetailApi.as_view(),
        name='terminal-detail-update-delete-api'),
    url(r'^v1/terminal-heatbeat/$', api.TerminalHeatbeatApi.as_view(), name='terminal-heatbeat-api'),
]
