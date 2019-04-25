# -*- coding: utf-8 -*-
#

from django.urls import path

from .. import api

app_name = 'common'

urlpatterns = [
    path('resources-id/cache/', api.ResourcesIdCacheApi.as_view(), name='resources-id-cache'),
    ]