# -*- coding: utf-8 -*-
#

from django.urls import path
from django.conf import settings

from .. import api

app_name = 'common'

urlpatterns = [
    path('resources/cache/', api.ResourcesIDCacheApi.as_view(), name='resources-cache'),
    path('countries/', api.CountryListApi.as_view(), name='resources-cache'),
]

if settings.JDMC_ENABLED:
    urlpatterns.append(
        path('jdmc/sso-token/', api.JdmcSSOTokenAPI.as_view(), name='jdmc-sso-token')
    )
