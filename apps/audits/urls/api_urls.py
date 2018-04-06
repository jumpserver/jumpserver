# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from .. import api


app_name = "audits"

router = DefaultRouter()
router.register(r'v1/ftp-log', api.FTPLogViewSet, 'ftp-log')

urlpatterns = [
#    url(r'^v1/celery/task/(?P<pk>[0-9a-zA-Z\-]{36})/log/$', api.CeleryTaskLogApi.as_view(), name='celery-task-log'),
]

urlpatterns += router.urls
