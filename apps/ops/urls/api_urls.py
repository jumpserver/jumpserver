# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_bulk.routes import BulkRouter
from .. import api

app_name = "ops"

router = DefaultRouter()
bulk_router = BulkRouter()

router.register(r'adhoc', api.AdHocViewSet, 'adhoc')
router.register(r'adhoc-executions', api.AdHocExecutionViewSet, 'execution')
router.register(r'celery/period-tasks', api.CeleryPeriodTaskViewSet, 'celery-period-task')
router.register(r'celery/tasks', api.CeleryTaskViewSet, 'celery-task')
router.register(r'celery/task-executions', api.CeleryTaskExecutionViewSet, 'task-execution')

urlpatterns = [
    path('celery/task/<uuid:pk>/log/', api.CeleryTaskExecutionLogApi.as_view(), name='celery-task-log'),
    path('celery/task/<uuid:pk>/result/', api.CeleryResultApi.as_view(), name='celery-result'),

    path('ansible/task/<uuid:pk>/log/', api.AnsibleTaskLogApi.as_view(), name='ansible-task-log'),
]

urlpatterns += router.urls
urlpatterns += bulk_router.urls
