#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from ..api import v2 as api

app_name = 'terminal'

router = BulkRouter()
router.register(r'terminal', api.TerminalViewSet, 'terminal')


urlpatterns = [
    path('terminal-registrations/', api.TerminalRegistrationApi.as_view(),
         name='terminal-registration')
]

urlpatterns += router.urls
