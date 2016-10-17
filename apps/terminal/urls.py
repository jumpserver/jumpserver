#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

from django.conf.urls import url

import views
import api

app_name = 'terminal'

urlpatterns = [
    url(r'^terminal$', views.TerminalListView.as_view(), name='terminal-list'),
]

urlpatterns += [
    url(r'^v1/terminal/$', api.TerminalApi.as_view(), name='terminal-list-create-api'),
]
