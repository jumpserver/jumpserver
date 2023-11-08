#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from . import api

app_name = 'labels'

router = BulkRouter()
router.register(r'labels', api.LabelViewSet, 'label')
router.register(r'labeled-resources', api.LabeledResourceViewSet, 'labeled-resource')

urlpatterns = [
    path('resource-types/', api.ContentTypeListApi.as_view(), name='resource-type-list'),
]

urlpatterns += router.urls
