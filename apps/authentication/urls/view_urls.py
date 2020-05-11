# coding:utf-8
#

from django.urls import path, include

from .. import views

app_name = 'authentication'

urlpatterns = [
    # login
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('login/otp/', views.UserLoginOtpView.as_view(), name='login-otp'),
    path('login/wait-confirm/', views.UserLoginWaitConfirmView.as_view(), name='login-wait-confirm'),
    path('login/guard/', views.UserLoginGuardView.as_view(), name='login-guard'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),

    # openid
    path('cas/', include(('authentication.backends.cas.urls', 'authentication'), namespace='cas')),
    path('openid/', include(('jms_oidc_rp.urls', 'authentication'), namespace='openid')),
]
