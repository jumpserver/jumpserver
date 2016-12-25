#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.conf.urls import url
from rest_framework import routers

from .. import api

app_name = 'terminal'

router = routers.DefaultRouter()
router.register(r'v1/terminal/heatbeat', api.TerminalHeatbeatViewSet, 'terminal-heatbeat')
router.register(r'v1/terminal', api.TerminalViewSet, 'terminal')

urlpatterns = [
    url(r'v1/register$', api.TerminalRegisterView.as_view(), name='api-terminal-register')
]

urlpatterns += router.urls