#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~
#
from __future__ import absolute_import

from django.urls import path, include
from rest_framework_bulk.routes import BulkRouter
from .. import api_v2 as api

app_name = 'users'

router = BulkRouter()
router.register(r'service-account-registrations',
                api.ServiceAccountRegistrationViewSet,
                'service-account-registration')


urlpatterns = [
    # path('token/', api.UserToken.as_view(), name='user-token'),
]
urlpatterns += router.urls


