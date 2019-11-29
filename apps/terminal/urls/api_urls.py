#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.urls import path, include, re_path
from rest_framework_bulk.routes import BulkRouter

from common import api as capi
from .. import api

app_name = 'terminal'

router = BulkRouter()
router.register(r'sessions', api.SessionViewSet, 'session')
router.register(r'terminals/(?P<terminal>[a-zA-Z0-9\-]{36})?/?status', api.StatusViewSet, 'terminal-status')
router.register(r'terminals/(?P<terminal>[a-zA-Z0-9\-]{36})?/?sessions', api.SessionViewSet, 'terminal-sessions')
router.register(r'terminals', api.TerminalViewSet, 'terminal')
router.register(r'tasks', api.TaskViewSet, 'tasks')
router.register(r'commands', api.CommandViewSet, 'command')
router.register(r'status', api.StatusViewSet, 'status')
router.register(r'replay-storages', api.ReplayStorageViewSet, 'replay-storage')
router.register(r'command-storages', api.CommandStorageViewSet, 'command-storage')

urlpatterns = [
    path('sessions/<uuid:pk>/replay/',
         api.SessionReplayViewSet.as_view({'get': 'retrieve', 'post': 'create'}),
         name='session-replay'),
    path('tasks/kill-session/', api.KillSessionAPI.as_view(), name='kill-session'),
    path('terminals/<uuid:terminal>/access-key/', api.TerminalTokenApi.as_view(),
         name='terminal-access-key'),
    path('terminals/config/', api.TerminalConfig.as_view(), name='terminal-config'),
    path('commands/export/', api.CommandExportApi.as_view(), name="command-export"),
    path('replay-storages/<uuid:pk>/test-connective/', api.ReplayStorageTestConnectiveApi.as_view(), name='replay-storage-test-connective'),
    path('command-storages/<uuid:pk>/test-connective/', api.CommandStorageTestConnectiveApi.as_view(), name='command-storage-test-connective')
    # v2: get session's replay
    # path('v2/sessions/<uuid:pk>/replay/',
    #     api.SessionReplayV2ViewSet.as_view({'get': 'retrieve'}),
    #     name='session-replay-v2'),
]

old_version_urlpatterns = [
    re_path('(?P<resource>terminal|command)/.*', capi.redirect_plural_name_api)
]

urlpatterns += router.urls + old_version_urlpatterns



