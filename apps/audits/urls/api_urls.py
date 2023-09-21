# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.urls.conf import path
from rest_framework.routers import DefaultRouter

from .. import api

app_name = "audits"

router = DefaultRouter()
router.register(r'ftp-logs', api.FTPLogViewSet, 'ftp-log')
router.register(r'login-logs', api.UserLoginLogViewSet, 'login-log')
router.register(r'operate-logs', api.OperateLogViewSet, 'operate-log')
router.register(r'password-change-logs', api.PasswordChangeLogViewSet, 'password-change-log')
router.register(r'job-logs', api.JobAuditViewSet, 'job-log')
router.register(r'my-login-logs', api.MyLoginLogViewSet, 'my-login-log')
router.register(r'user-sessions', api.UserSessionViewSet, 'user-session')

urlpatterns = [
    path('activities/', api.ResourceActivityAPIView.as_view(), name='resource-activities'),
]

urlpatterns += router.urls
