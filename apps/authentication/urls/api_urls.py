# coding:utf-8
#
from django.urls import path
from rest_framework.routers import DefaultRouter

from .. import api

app_name = 'authentication'
router = DefaultRouter()
router.register('access-keys', api.AccessKeyViewSet, 'access-key')
router.register('sso', api.SSOViewSet, 'sso')
router.register('connection-token', api.UserConnectionTokenViewSet, 'connection-token')


urlpatterns = [
    # path('token/', api.UserToken.as_view(), name='user-token'),
    path('wecom/qr/unbind/', api.WeComQRUnBindForUserApi.as_view(), name='wecom-qr-unbind'),
    path('wecom/qr/unbind/<uuid:user_id>/', api.WeComQRUnBindForAdminApi.as_view(), name='wecom-qr-unbind-for-admin'),

    path('dingtalk/qr/unbind/', api.DingTalkQRUnBindForUserApi.as_view(), name='dingtalk-qr-unbind'),
    path('dingtalk/qr/unbind/<uuid:user_id>/', api.DingTalkQRUnBindForAdminApi.as_view(), name='dingtalk-qr-unbind-for-admin'),

    path('auth/', api.TokenCreateApi.as_view(), name='user-auth'),
    path('tokens/', api.TokenCreateApi.as_view(), name='auth-token'),
    path('mfa/challenge/', api.MFAChallengeApi.as_view(), name='mfa-challenge'),
    path('otp/verify/', api.UserOtpVerifyApi.as_view(), name='user-otp-verify'),
    path('password/verify/', api.UserPasswordVerifyApi.as_view(), name='user-password-verify'),
    path('login-confirm-ticket/status/', api.TicketStatusApi.as_view(), name='login-confirm-ticket-status'),
    path('login-confirm-settings/<uuid:user_id>/', api.LoginConfirmSettingUpdateApi.as_view(), name='login-confirm-setting-update')
]

urlpatterns += router.urls
