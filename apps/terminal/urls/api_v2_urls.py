#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from .. import api_v2

app_name = 'terminal'

router = BulkRouter()
router.register(r'terminal', api_v2.TerminalViewSet, 'terminal')


urlpatterns = [
]

urlpatterns += router.urls
