# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_bulk.routes import BulkRouter
from rest_framework_nested import routers

from .. import api

app_name = "ops"

router = DefaultRouter()
bulk_router = BulkRouter()

router.register(r'adhoc', api.AdHocViewSet, 'adhoc')
router.register(r'adhoc-executions', api.AdHocExecutionViewSet, 'execution')
router.register(r'celery/period-tasks', api.CeleryPeriodTaskViewSet, 'celery-period-task')

router.register(r'tasks', api.CeleryTaskViewSet, 'task')

task_router = routers.NestedDefaultRouter(router, r'tasks', lookup='task')
task_router.register(r'executions', api.CeleryTaskExecutionViewSet, 'task-execution')

urlpatterns = [

    path('celery/task/<uuid:name>/task-execution/<uuid:pk>/log/', api.CeleryTaskExecutionLogApi.as_view(),
         name='celery-task-execution-log'),
    path('celery/task/<uuid:name>/task-execution/<uuid:pk>/result/', api.CeleryResultApi.as_view(),
         name='celery-task-execution-result'),

    path('ansible/task-execution/<uuid:pk>/log/', api.AnsibleTaskLogApi.as_view(), name='ansible-task-log'),
]

urlpatterns += (router.urls + bulk_router.urls + task_router.urls)
