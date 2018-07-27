# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from .. import api


app_name = "audits"

router = DefaultRouter()
router.register(r'ftp-log', api.FTPLogViewSet, 'ftp-log')

urlpatterns = [
]

urlpatterns += router.urls
