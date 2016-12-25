#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.conf.urls import url
from rest_framework import routers

from .. import api

app_name = 'applications'

router = routers.DefaultRouter()
router.register(r'v1/terminal', api.TerminalViewSet, 'terminal')
router.register(r'v1/terminal/heatbeat', api.TerminalHeatbeatViewSet, 'terminal-heatbeat')

urlpatterns = [
    url(r'v1/terminal/register$', api.TerminalRegisterView.as_view(), name='terminal-register')
]

urlpatterns += router.urls