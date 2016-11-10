#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

from django.conf.urls import url
from rest_framework import routers

import views
import api

app_name = 'terminal'

urlpatterns = [
    url(r'^terminal$', views.TerminalListView.as_view(), name='terminal-list'),
    url(r'^terminal/(?P<pk>\d+)/update$', views.TerminalUpdateView.as_view(), name='terminal-update'),
]

router = routers.DefaultRouter()
router.register(r'v1/terminal', api.TerminalViewSet, 'api-terminal')

urlpatterns += [
    url(r'^v1/terminal/heatbeat/$', api.TerminalHeatbeatApi.as_view(), name='terminal-heatbeat-api'),
]

urlpatterns += router.urls
