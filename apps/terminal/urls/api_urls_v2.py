#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.urls import path, re_path
from rest_framework_bulk.routes import BulkRouter

from common import api as capi
from .. import api_v2 as api

app_name = 'terminal'

router = BulkRouter()
router.register(r'terminals', api.TerminalViewSet, 'terminal')


urlpatterns = [
    path('terminal-registrations/', api.TerminalRegistrationApi.as_view(),
         name='terminal-registration')
]

old_version_urlpatterns = [
    re_path('(?P<resource>terminal)/.*', capi.redirect_plural_name_api)
]

urlpatterns += router.urls
