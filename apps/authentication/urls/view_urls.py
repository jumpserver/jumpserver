# coding:utf-8
#

from django.db.transaction import non_atomic_requests
from django.urls import path, include

from users import views as users_view
from .. import views

app_name = 'authentication'

urlpatterns = [
    # login
    path('login/', non_atomic_requests(views.UserLoginView.as_view()), name='login'),
    path('login/mfa/', views.UserLoginMFAView.as_view(), name='login-mfa'),
    path('login/wait-confirm/', views.UserLoginWaitConfirmView.as_view(), name='login-wait-confirm'),
    path('login/guard/', views.UserLoginGuardView.as_view(), name='login-guard'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),

    # 原来在users中的
    path('password/forget/previewing/', users_view.UserForgotPasswordPreviewingView.as_view(),
         name='forgot-previewing'),
    path('password/forgot/', users_view.UserForgotPasswordView.as_view(), name='forgot-password'),
    path('password/reset/', users_view.UserResetPasswordView.as_view(), name='reset-password'),
    path('password/verify/', users_view.UserVerifyPasswordView.as_view(), name='user-verify-password'),

    path('wecom/bind/start/', views.WeComEnableStartView.as_view(), name='wecom-bind-start'),
    path('wecom/qr/bind/', views.WeComQRBindView.as_view(), name='wecom-qr-bind'),
    path('wecom/qr/login/', views.WeComQRLoginView.as_view(), name='wecom-qr-login'),
    path('wecom/qr/bind/callback/', views.WeComQRBindCallbackView.as_view(),
         name='wecom-qr-bind-callback'),
    path('wecom/qr/login/callback/', views.WeComQRLoginCallbackView.as_view(), name='wecom-qr-login-callback'),
    path('wecom/oauth/login/', views.WeComOAuthLoginView.as_view(), name='wecom-oauth-login'),
    path('wecom/oauth/login/callback/', views.WeComOAuthLoginCallbackView.as_view(), name='wecom-oauth-login-callback'),

    path('dingtalk/bind/start/', views.DingTalkEnableStartView.as_view(), name='dingtalk-bind-start'),
    path('dingtalk/qr/bind/', views.DingTalkQRBindView.as_view(), name='dingtalk-qr-bind'),
    path('dingtalk/qr/login/', views.DingTalkQRLoginView.as_view(), name='dingtalk-qr-login'),
    path('dingtalk/qr/bind/<uuid:user_id>/callback/', views.DingTalkQRBindCallbackView.as_view(),
         name='dingtalk-qr-bind-callback'),
    path('dingtalk/qr/login/callback/', views.DingTalkQRLoginCallbackView.as_view(), name='dingtalk-qr-login-callback'),
    path('dingtalk/oauth/login/', views.DingTalkOAuthLoginView.as_view(), name='dingtalk-oauth-login'),
    path('dingtalk/oauth/login/callback/', views.DingTalkOAuthLoginCallbackView.as_view(),
         name='dingtalk-oauth-login-callback'),

    path('feishu/bind/start/', views.FeiShuEnableStartView.as_view(), name='feishu-bind-start'),
    path('feishu/qr/bind/', views.FeiShuQRBindView.as_view(), name='feishu-qr-bind'),
    path('feishu/qr/login/', views.FeiShuQRLoginView.as_view(), name='feishu-qr-login'),
    path('feishu/qr/bind/callback/', views.FeiShuQRBindCallbackView.as_view(), name='feishu-qr-bind-callback'),
    path('feishu/qr/login/callback/', views.FeiShuQRLoginCallbackView.as_view(), name='feishu-qr-login-callback'),

    path('slack/bind/start/', views.SlackEnableStartView.as_view(), name='slack-bind-start'),
    path('slack/qr/bind/', views.SlackQRBindView.as_view(), name='slack-qr-bind'),
    path('slack/qr/login/', views.SlackQRLoginView.as_view(), name='slack-qr-login'),
    path('slack/qr/bind/callback/', views.SlackQRBindCallbackView.as_view(), name='slack-qr-bind-callback'),
    path('slack/qr/login/callback/', views.SlackQRLoginCallbackView.as_view(), name='slack-qr-login-callback'),

    # Profile
    path('profile/pubkey/generate/', users_view.UserPublicKeyGenerateView.as_view(), name='user-pubkey-generate'),
    path('profile/mfa/', users_view.MFASettingView.as_view(), name='user-mfa-setting'),

    # OTP Setting
    path('profile/otp/enable/start/', users_view.UserOtpEnableStartView.as_view(), name='user-otp-enable-start'),
    path('profile/otp/enable/install-app/', users_view.UserOtpEnableInstallAppView.as_view(),
         name='user-otp-enable-install-app'),
    path('profile/otp/enable/bind/', users_view.UserOtpEnableBindView.as_view(), name='user-otp-enable-bind'),
    path('profile/otp/disable/', users_view.UserOtpDisableView.as_view(),
         name='user-otp-disable'),

    # other authentication protocol
    path('cas/', include(('authentication.backends.cas.urls', 'authentication'), namespace='cas')),
    path('openid/', include(('authentication.backends.oidc.urls', 'authentication'), namespace='openid')),
    path('saml2/', include(('authentication.backends.saml2.urls', 'authentication'), namespace='saml2')),
    path('oauth2/', include(('authentication.backends.oauth2.urls', 'authentication'), namespace='oauth2')),

    path('captcha/', include('captcha.urls')),
]
