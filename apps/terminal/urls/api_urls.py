#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.conf.urls import url
from rest_framework import routers

from .. import api

app_name = 'terminal'

router = routers.DefaultRouter()
router.register(r'v1/terminal/(?P<terminal>[a-zA-Z0-9\-]{36})?/?status', api.StatusViewSet, 'terminal-status')
router.register(r'v1/terminal/(?P<terminal>[a-zA-Z0-9\-]{36})?/?sessions', api.SessionViewSet, 'terminal-sessions')
router.register(r'v1/tasks', api.TaskViewSet, 'tasks')
router.register(r'v1/terminal', api.TerminalViewSet, 'terminal')
router.register(r'v1/command', api.CommandViewSet, 'command')

urlpatterns = [
    url(r'^v1/sessions/(?P<pk>[0-9a-zA-Z\-]{36})/replay/$',
        api.SessionReplayViewSet.as_view({'get': 'retrieve', 'post': 'create'}),
        name='session-replay'),
]

urlpatterns += router.urls
