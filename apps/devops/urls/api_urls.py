#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.conf.urls import url
from rest_framework import routers
from .. import api

app_name = 'devops'

router = routers.DefaultRouter()
router.register(r'v1/tasks', api.TaskListViewSet, 'task')
router.register(r'v1/records', api.RecordViewSet, 'record')
router.register(r'v1/tasks-opt', api.TaskOperationViewSet, 'task-opt')
router.register(r'v1/roles', api.AnsibleRoleViewSet, 'role')
router.register(r'v1/variables', api.VariableViewSet, 'variable')

urlpatterns = [
    url(r'^v1/roles/install/$', api.InstallRoleView.as_view(), name='role-install'),
    url(r'^v1/tasks/(?P<pk>\d+)/groups/$', api.TaskUpdateGroupApi.as_view(), name='task-update-group'),
    url(r'^v1/tasks/(?P<pk>\d+)/assets/$', api.TaskUpdateAssetApi.as_view(), name='task-update-asset'),
    url(r'^v1/tasks/(?P<pk>\d+)/system-user/$', api.TaskUpdateSystemUserApi.as_view(), name='task-update-system-user'),
    url(r'^v1/tasks/(?P<pk>\d+)/execute/$', api.TaskExecuteApi.as_view(), name='task-execute'),
    url(r'^v1/variables/(?P<pk>\d+)/vars/$', api.VariableVarsApi.as_view(), name='variable-vars'),
    url(r'^v1/variables/(?P<pk>\d+)/vars/add/$', api.VariableAddVarsApi.as_view(), name='variable-add-vars'),
    url(r'^v1/variables/(?P<pk>\d+)/vars/delete/$', api.VariableDeleteVarsApi.as_view(), name='variable-delete-vars'),
    url(r'^v1/variables/(?P<pk>\d+)/groups/$', api.VariableUpdateGroupApi.as_view(), name='variable-update-group'),
    url(r'^v1/variables/(?P<pk>\d+)/assets/$', api.VariableUpdateAssetApi.as_view(), name='variable-update-asset'),
    url(r'^v1/variables/(?P<pk>\d+)/assets/get/$', api.VariableGetAssetApi.as_view(), name='variable-get-asset'),
    url(r'^v1/variables/(?P<pk>\d+)/groups/get/$', api.VariableGetGroupApi.as_view(), name='variable-get-group'),
]

urlpatterns += router.urls
