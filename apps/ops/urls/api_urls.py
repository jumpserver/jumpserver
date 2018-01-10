# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from .. import api


app_name = "ops"

router = DefaultRouter()
router.register(r'v1/tasks', api.TaskViewSet, 'task')
router.register(r'v1/adhoc', api.AdHocViewSet, 'adhoc')
router.register(r'v1/history', api.AdHocRunHistorySet, 'history')

urlpatterns = [
    url(r'^v1/tasks/(?P<pk>[0-9a-zA-Z\-]{36})/run/$', api.TaskRun.as_view(), name='task-run'),
]

urlpatterns += router.urls
