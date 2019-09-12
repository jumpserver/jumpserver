# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.urls.conf import re_path
from rest_framework.routers import DefaultRouter

from common import api as capi
from .. import api


app_name = "audits"

router = DefaultRouter()
router.register(r'ftp-logs', api.FTPLogViewSet, 'ftp-log')

urlpatterns = [
]

old_version_urlpatterns = [
    re_path('(?P<resource>ftp-log)/.*', capi.redirect_plural_name_api)
]

urlpatterns += router.urls
