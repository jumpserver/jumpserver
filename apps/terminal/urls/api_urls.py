#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.urls import path, include
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = 'terminal'

router = BulkRouter()
router.register(r'sessions', api.SessionViewSet, 'session')
router.register(r'terminal/(?P<terminal>[a-zA-Z0-9\-]{36})?/?status', api.StatusViewSet, 'terminal-status')
router.register(r'terminal/(?P<terminal>[a-zA-Z0-9\-]{36})?/?sessions', api.SessionViewSet, 'terminal-sessions')
router.register(r'terminal', api.TerminalViewSet, 'terminal')
router.register(r'tasks', api.TaskViewSet, 'tasks')
router.register(r'command', api.CommandViewSet, 'command')
router.register(r'status', api.StatusViewSet, 'status')

urlpatterns = [
    path('sessions/<uuid:pk>/replay/',
         api.SessionReplayViewSet.as_view({'get': 'retrieve', 'post': 'create'}),
         name='session-replay'),
    path('tasks/kill-session/', api.KillSessionAPI.as_view(), name='kill-session'),
    path('terminal/<uuid:terminal>/access-key/', api.TerminalTokenApi.as_view(),
         name='terminal-access-key'),
    path('terminal/config/', api.TerminalConfig.as_view(), name='terminal-config'),
    # v2: get session's replay
    # path('v2/sessions/<uuid:pk>/replay/',
    #     api.SessionReplayV2ViewSet.as_view({'get': 'retrieve'}),
    #     name='session-replay-v2'),
]

urlpatterns += router.urls



