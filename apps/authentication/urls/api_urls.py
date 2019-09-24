# coding:utf-8
#

from __future__ import absolute_import

from django.urls import path
from rest_framework.routers import DefaultRouter

from .. import api

router = DefaultRouter()
router.register('access-keys', api.AccessKeyViewSet, 'access-key')


app_name = 'authentication'


urlpatterns = [
    # path('token/', api.UserToken.as_view(), name='user-token'),
    path('auth/', api.UserAuthApi.as_view(), name='user-auth'),
    path('tokens/', api.TokenCreateApi.as_view(), name='auth-token'),
    path('mfa/challenge/', api.MFAChallengeApi.as_view(), name='mfa-challenge'),
    path('connection-token/',
         api.UserConnectionTokenApi.as_view(), name='connection-token'),
    path('otp/auth/', api.UserOtpAuthApi.as_view(), name='user-otp-auth'),
    path('otp/verify/', api.UserOtpVerifyApi.as_view(), name='user-otp-verify'),
]

urlpatterns += router.urls

