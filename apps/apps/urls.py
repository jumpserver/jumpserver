#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

from django.conf.urls import url

import views
import api

app_name = 'apps'

urlpatterns = [
    url(r'^apps$', views.TerminalListView.as_view(), name='apps-list'),
]

urlpatterns += [
    url(r'^v1/apps/$', api.TerminalApi.as_view(), name='apps-list-create-api'),
]
