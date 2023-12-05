#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from rest_framework_bulk.routes import BulkRouter

from . import api

app_name = 'labels'

router = BulkRouter()
router.register(r'labels', api.LabelViewSet, 'label')
router.register(r'labels/(?P<label>.*)/resource-types/(?P<res_type>.*)/resources',
                api.LabelContentTypeResourceViewSet, 'label-content-type-resource')
router.register(r'labeled-resources', api.LabeledResourceViewSet, 'labeled-resource')
router.register(r'resource-types', api.ContentTypeViewSet, 'content-type')

urlpatterns = [
]

urlpatterns += router.urls
