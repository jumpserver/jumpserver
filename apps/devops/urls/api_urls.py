#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.conf.urls import url
from rest_framework import routers
from .. import api

app_name = 'devops'

router = routers.DefaultRouter()
router.register(r'v1/tasks', api.TaskViewSet, 'task')
router.register(r'v1/roles', api.AnsibleRoleViewSet, 'role')

urlpatterns = [
    url(r'^v1/roles/install/$', api.InstallRoleView.as_view(), name='role-install'),
]

urlpatterns += router.urls
