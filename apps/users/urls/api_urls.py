#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~
#
from __future__ import absolute_import

from django.conf.urls import url
from rest_framework_bulk.routes import BulkRouter
from .. import api

app_name = 'users'

router = BulkRouter()
router.register(r'users', api.UserViewSet, 'user')
router.register(r'groups', api.UserGroupViewSet, 'user-group')


urlpatterns = [
    # url(r'', api.UserListView.as_view()),
    url(r'^token/$', api.UserToken.as_view(), name='user-token'),
    url(r'^connection-token/$', api.UserConnectionTokenApi.as_view(), name='connection-token'),
    url(r'^profile/$', api.UserProfile.as_view(), name='user-profile'),
    url(r'^auth/$', api.UserAuthApi.as_view(), name='user-auth'),
    url(r'^otp/auth/$', api.UserOtpAuthApi.as_view(), name='user-otp-auth'),
    url(r'^users/(?P<pk>[0-9a-zA-Z\-]{36})/password/$',
        api.ChangeUserPasswordApi.as_view(), name='change-user-password'),
    url(r'^users/(?P<pk>[0-9a-zA-Z\-]{36})/password/reset/$',
        api.UserResetPasswordApi.as_view(), name='user-reset-password'),
    url(r'^users/(?P<pk>[0-9a-zA-Z\-]{36})/pubkey/reset/$',
        api.UserResetPKApi.as_view(), name='user-public-key-reset'),
    url(r'^users/(?P<pk>[0-9a-zA-Z\-]{36})/pubkey/update/$',
        api.UserUpdatePKApi.as_view(), name='user-public-key-update'),
    url(r'^users/(?P<pk>[0-9a-zA-Z\-]{36})/groups/$',
        api.UserUpdateGroupApi.as_view(), name='user-update-group'),
    url(r'^groups/(?P<pk>[0-9a-zA-Z\-]{36})/users/$',
        api.UserGroupUpdateUserApi.as_view(), name='user-group-update-user'),
]

urlpatterns += router.urls
