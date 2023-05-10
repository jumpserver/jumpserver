# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = "ops"

router = DefaultRouter()
bulk_router = BulkRouter()

bulk_router.register(r'adhocs', api.AdHocViewSet, 'adhoc')
bulk_router.register(r'playbooks', api.PlaybookViewSet, 'playbook')
bulk_router.register(r'jobs', api.JobViewSet, 'job')
bulk_router.register(r'job-executions', api.JobExecutionViewSet, 'job-execution')

router.register(r'celery/period-tasks', api.CeleryPeriodTaskViewSet, 'celery-period-task')

router.register(r'tasks', api.CeleryTaskViewSet, 'task')
router.register(r'task-executions', api.CeleryTaskExecutionViewSet, 'task-executions')

urlpatterns = [
    path('playbook/<uuid:pk>/file/', api.PlaybookFileBrowserAPIView.as_view(), name='playbook-file'),
    path('variables/help/', api.JobRunVariableHelpAPIView.as_view(), name='variable-help'),
    path('job-execution/asset-detail/', api.JobAssetDetail.as_view(), name='asset-detail'),
    path('job-execution/task-detail/<uuid:task_id>/', api.JobExecutionTaskDetail.as_view(), name='task-detail'),
    path('username-hints/', api.UsernameHintsAPI.as_view(), name='username-hints'),
    path('ansible/job-execution/<uuid:pk>/log/', api.AnsibleTaskLogApi.as_view(), name='job-execution-log'),

    path('celery/task/<uuid:name>/task-execution/<uuid:pk>/log/', api.CeleryTaskExecutionLogApi.as_view(),
         name='celery-task-execution-log'),
    path('celery/task/<uuid:name>/task-execution/<uuid:pk>/result/', api.CeleryResultApi.as_view(),
         name='celery-task-execution-result'),

]

urlpatterns += (router.urls + bulk_router.urls)
