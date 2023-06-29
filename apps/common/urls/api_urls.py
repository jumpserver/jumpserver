# -*- coding: utf-8 -*-
#

from django.urls import path

from .. import api

app_name = 'common'

urlpatterns = [
    path('resources/cache/', api.ResourcesIDCacheApi.as_view(), name='resources-cache'),
    path('flash-message/', api.FlashMessageMsgApi.as_view(), name='flash-message'),
]
