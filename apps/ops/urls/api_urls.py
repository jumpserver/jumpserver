# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from .. import api


app_name = "ops"

router = DefaultRouter()
router.register(r'tasks', api.TaskViewSet, 'task')
router.register(r'adhoc', api.AdHocViewSet, 'adhoc')
router.register(r'history', api.AdHocRunHistorySet, 'history')

urlpatterns = [
    url(r'^tasks/(?P<pk>[0-9a-zA-Z\-]{36})/run/$', api.TaskRun.as_view(), name='task-run'),
    url(r'^celery/task/(?P<pk>[0-9a-zA-Z\-]{36})/log/$', api.CeleryTaskLogApi.as_view(), name='celery-task-log'),
]

urlpatterns += router.urls
