#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = 'terminal'

router = BulkRouter()
router.register(r'sessions', api.SessionViewSet, 'session')
router.register(r'terminals/((?P<terminal>[^/.]{36})/)?status', api.StatusViewSet, 'terminal-status')
router.register(r'terminals/((?P<terminal>[^/.]{36})/)?sessions', api.SessionViewSet, 'terminal-sessions')
router.register(r'terminals', api.TerminalViewSet, 'terminal')
router.register(r'tasks', api.TaskViewSet, 'tasks')
router.register(r'commands', api.CommandViewSet, 'command')
router.register(r'status', api.StatusViewSet, 'status')
router.register(r'replay-storages', api.ReplayStorageViewSet, 'replay-storage')
router.register(r'command-storages', api.CommandStorageViewSet, 'command-storage')
router.register(r'session-sharings', api.SessionSharingViewSet, 'session-sharing')
router.register(r'session-join-records', api.SessionJoinRecordsViewSet, 'session-sharing-record')
router.register(r'endpoints', api.EndpointViewSet, 'endpoint')
router.register(r'endpoint-rules', api.EndpointRuleViewSet, 'endpoint-rule')
router.register(r'applets', api.AppletViewSet, 'applet')
router.register(r'applet-hosts/((?P<host>[^/.]+)/)?accounts', api.AppletHostAccountsViewSet, 'applet-host-account')
router.register(r'applet-hosts/((?P<host>[^/.]+)/)?applets', api.AppletHostAppletViewSet, 'applet-host-applet')
router.register(r'applet-hosts', api.AppletHostViewSet, 'applet-host')
router.register(r'applet-publications', api.AppletPublicationViewSet, 'applet-publication')
router.register(r'applet-host-deployments', api.AppletHostDeploymentViewSet, 'applet-host-deployment')
router.register(r'db-listen-ports', api.DBListenPortViewSet, 'db-listen-ports')
router.register(r'virtual-apps', api.VirtualAppViewSet, 'virtual-app')
router.register(r'app-providers', api.AppProviderViewSet, 'app-provider')
router.register(r'app-providers/((?P<provider>[^/.]+)/)?apps', api.AppProviderAppViewSet, 'app-provider-app')
router.register(r'virtual-app-publications', api.VirtualAppPublicationViewSet, 'virtual-app-publication')

urlpatterns = [
    path('my-sessions/', api.MySessionAPIView.as_view(), name='my-session'),
    path('terminal-registrations/', api.TerminalRegistrationApi.as_view(), name='terminal-registration'),
    path('registration/', api.TerminalRegistrationApi.as_view(), name='registration'),
    path('sessions/join/validate/', api.SessionJoinValidateAPI.as_view(), name='join-session-validate'),
    path('sessions/<uuid:pk>/replay/',
         api.SessionReplayViewSet.as_view({'get': 'retrieve', 'post': 'create'}),
         name='session-replay'),
    path('tasks/kill-session/', api.KillSessionAPI.as_view(), name='kill-session'),
    path('tasks/kill-session-for-ticket/', api.KillSessionForTicketAPI.as_view(), name='kill-session-for-ticket'),
    path('terminals/config/', api.TerminalConfig.as_view(), name='terminal-config'),
    path('commands/insecure-command/', api.InsecureCommandAlertAPI.as_view(), name="command-alert"),
    path('replay-storages/<uuid:pk>/test-connective/', api.ReplayStorageTestConnectiveApi.as_view(),
         name='replay-storage-test-connective'),
    path('command-storages/<uuid:pk>/test-connective/', api.CommandStorageTestConnectiveApi.as_view(),
         name='command-storage-test-connective'),
    # components
    path('components/metrics/', api.ComponentsMetricsAPIView.as_view(), name='components-metrics'),
    path('components/connect-methods/', api.ConnectMethodListApi.as_view(), name='connect-methods'),
]

urlpatterns += router.urls
