# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.urls.conf import re_path
from rest_framework.routers import DefaultRouter

from common import api as capi
from .. import api


app_name = "audits"

router = DefaultRouter()
router.register(r'ftp-logs', api.FTPLogViewSet, 'ftp-log')
router.register(r'login-logs', api.UserLoginLogViewSet, 'login-log')
router.register(r'operate-logs', api.OperateLogViewSet, 'operate-log')
router.register(r'password-change-logs', api.PasswordChangeLogViewSet, 'password-change-log')
router.register(r'command-execution-logs', api.CommandExecutionViewSet, 'command-execution-log')
router.register(r'command-executions-hosts-relations', api.CommandExecutionHostRelationViewSet, 'command-executions-hosts-relation')


urlpatterns = [
]

old_version_urlpatterns = [
    re_path('(?P<resource>ftp-log)/.*', capi.redirect_plural_name_api)
]

urlpatterns += router.urls
