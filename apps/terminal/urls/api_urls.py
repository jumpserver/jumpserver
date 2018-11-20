#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.urls import path, include

from . import api_v1_urls, api_v2_urls

app_name = 'terminal'


urlpatterns = [
    path('v1/', include(api_v1_urls.urlpatterns)),
    path('v2/', include(api_v2_urls, namespace='v2')),
]
