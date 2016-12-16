#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~
#
from __future__ import absolute_import

from django.conf.urls import url
from rest_framework_bulk.routes import BulkRouter
from .. import api

app_name = 'users'

router = BulkRouter()
router.register(r'v1/users', api.UserViewSet, 'user')
router.register(r'v1/user-groups', api.UserGroupViewSet, 'user-group')
# router.register(r'v1/user-groups', api.AssetViewSet, 'api-groups')


urlpatterns = [
    url(r'^v1/users/token/$', api.UserToken.as_view(), name='user-token'),
    url(r'^v1/users/profile/$', api.UserProfile.as_view(), name='user-profile'),
    url(r'^v1/users/(?P<pk>\d+)/reset-password/$', api.UserResetPasswordApi.as_view(), name='user-reset-password'),
    url(r'^v1/users/(?P<pk>\d+)/reset-pk/$', api.UserResetPKApi.as_view(), name='user-reset-pk'),
    url(r'^v1/users/(?P<pk>\d+)/update-pk/$', api.UserUpdatePKApi.as_view(), name='user-update-pk'),
    url(r'^v1/users/(?P<pk>\d+)/groups/$',
        api.UserUpdateGroupApi.as_view(), name='user-update-group'),
    url(r'^v1/user-groups/(?P<pk>\d+)/users/$',
        api.UserGroupUpdateUserApi.as_view(), name='user-group-update-user'),
]

urlpatterns += router.urls
