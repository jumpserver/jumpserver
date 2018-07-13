#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.conf.urls import url
from rest_framework import routers

from .. import api

app_name = 'terminal'

router = routers.DefaultRouter()
router.register(r'terminal/(?P<terminal>[a-zA-Z0-9\-]{36})?/?status', api.StatusViewSet, 'terminal-status')
router.register(r'terminal/(?P<terminal>[a-zA-Z0-9\-]{36})?/?sessions', api.SessionViewSet, 'terminal-sessions')
router.register(r'tasks', api.TaskViewSet, 'tasks')
router.register(r'terminal', api.TerminalViewSet, 'terminal')
router.register(r'command', api.CommandViewSet, 'command')
router.register(r'sessions', api.SessionViewSet, 'session')
router.register(r'status', api.StatusViewSet, 'session')

urlpatterns = [
    url(r'^sessions/(?P<pk>[0-9a-zA-Z\-]{36})/replay/$',
        api.SessionReplayViewSet.as_view({'get': 'retrieve', 'post': 'create'}),
        name='session-replay'),
    url(r'^tasks/kill-session/', api.KillSessionAPI.as_view(), name='kill-session'),
    url(r'^terminal/(?P<terminal>[a-zA-Z0-9\-]{36})/access-key', api.TerminalTokenApi.as_view(),
        name='terminal-access-key'),
    url(r'^terminal/config', api.TerminalConfig.as_view(), name='terminal-config'),
    # v2: get session's replay
    url(r'^v2/sessions/(?P<pk>[0-9a-zA-Z\-]{36})/replay/$',
        api.SessionReplayV2ViewSet.as_view({'get': 'retrieve'}),
        name='session-replay-v2'),
]

urlpatterns += router.urls
