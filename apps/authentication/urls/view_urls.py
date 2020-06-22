# coding:utf-8
#

from django.urls import path, include

from .. import views
from users import views as users_view

app_name = 'authentication'

urlpatterns = [
    # login
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('login/otp/', views.UserLoginOtpView.as_view(), name='login-otp'),
    path('login/wait-confirm/', views.UserLoginWaitConfirmView.as_view(), name='login-wait-confirm'),
    path('login/guard/', views.UserLoginGuardView.as_view(), name='login-guard'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),

    # 原来在users中的
    path('password/forgot/', users_view.UserForgotPasswordView.as_view(), name='forgot-password'),
    path('password/forgot/sendmail-success/', users_view.UserForgotPasswordSendmailSuccessView.as_view(),
         name='forgot-password-sendmail-success'),
    path('password/reset/', users_view.UserResetPasswordView.as_view(), name='reset-password'),
    path('password/reset/success/', users_view.UserResetPasswordSuccessView.as_view(), name='reset-password-success'),
    path('password/verify/', users_view.UserVerifyPasswordView.as_view(), name='user-verify-password'),

    # Profile
    path('profile/pubkey/generate/', users_view.UserPublicKeyGenerateView.as_view(), name='user-pubkey-generate'),
    path('profile/otp/enable/start/', users_view.UserOtpEnableStartView.as_view(), name='user-otp-enable-start'),
    path('profile/otp/enable/install-app/', users_view.UserOtpEnableInstallAppView.as_view(),
         name='user-otp-enable-install-app'),
    path('profile/otp/enable/bind/', users_view.UserOtpEnableBindView.as_view(), name='user-otp-enable-bind'),
    path('profile/otp/disable/authentication/', users_view.UserDisableMFAView.as_view(),
         name='user-otp-disable-authentication'),
    path('profile/otp/update/', users_view.UserOtpUpdateView.as_view(), name='user-otp-update'),
    path('profile/otp/settings-success/', users_view.UserOtpSettingsSuccessView.as_view(), name='user-otp-settings-success'),
    path('first-login/', users_view.UserFirstLoginView.as_view(), name='user-first-login'),

    # openid
    path('cas/', include(('authentication.backends.cas.urls', 'authentication'), namespace='cas')),
    path('openid/', include(('jms_oidc_rp.urls', 'authentication'), namespace='openid')),
    path('captcha/', include('captcha.urls')),
]
