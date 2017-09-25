#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.conf.urls import url
from rest_framework import routers

app_name = 'devops'

router = routers.DefaultRouter()
# router.register(r'v1/terminal/heatbeat', api.TerminalHeatbeatViewSet, 'terminal-heatbeat')
# router.register(r'v1/terminal', api.TerminalViewSet, 'terminal')

urlpatterns = [
    # url(r'^v1/template/(?P<pk>\d+)/exec/$',
    #     api.TemplateTaskView.as_view(), name='template-task'),
]

urlpatterns += router.urls
