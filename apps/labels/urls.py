#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from rest_framework_bulk.routes import BulkRouter

from . import api

app_name = 'labels'

router = BulkRouter()
router.register(r'labels', api.LabelViewSet, 'label')

urlpatterns = router.urls
