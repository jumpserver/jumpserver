#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~
#
from __future__ import absolute_import

from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from authentication import api as auth_api
from .. import api

app_name = 'users'

router = BulkRouter()
router.register(r'users', api.UserViewSet, 'user')
router.register(r'groups', api.UserGroupViewSet, 'user-group')
router.register(r'users-groups-relations', api.UserUserGroupRelationViewSet, 'users-groups-relation')
router.register(r'service-account-registrations', api.ServiceAccountRegistrationViewSet, 'service-account-registration')
router.register(r'connection-token', auth_api.ConnectionTokenViewSet, 'connection-token')


urlpatterns = [
    path('profile/', api.UserProfileApi.as_view(), name='user-profile'),
    path('profile/password/', api.UserPasswordApi.as_view(), name='user-password'),
    path('profile/public-key/', api.UserPublicKeyApi.as_view(), name='user-public-key'),
    path('profile/mfa/reset/', api.UserResetMFAApi.as_view(), name='my-mfa-reset'),
    path('preference/', api.PreferenceApi.as_view(), name='preference'),
    path('users/<uuid:pk>/mfa/reset/', api.UserResetMFAApi.as_view(), name='user-reset-mfa'),
    path('users/<uuid:pk>/password/', api.UserChangePasswordApi.as_view(), name='change-user-password'),
    path('users/<uuid:pk>/password/reset/', api.UserResetPasswordApi.as_view(), name='user-reset-password'),
    path('users/<uuid:pk>/pubkey/reset/', api.UserResetPKApi.as_view(), name='user-public-key-reset'),
    path('users/<uuid:pk>/unblock/', api.UserUnblockPKApi.as_view(), name='user-unblock'),
]
urlpatterns += router.urls


