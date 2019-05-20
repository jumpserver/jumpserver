# coding:utf-8
#

from __future__ import absolute_import

from django.urls import path

from .. import api

app_name = 'authentication'


urlpatterns = [
    # path('token/', api.UserToken.as_view(), name='user-token'),
    path('auth/', api.UserAuthApi.as_view(), name='user-auth'),
    path('connection-token/',
         api.UserConnectionTokenApi.as_view(), name='connection-token'),
    path('otp/auth/', api.UserOtpAuthApi.as_view(), name='user-otp-auth'),
    path('otp/verify/', api.UserOtpVerifyApi.as_view(), name='user-otp-verify'),
]

