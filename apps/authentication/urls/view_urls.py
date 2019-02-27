# coding:utf-8
#

from django.urls import path

from .. import views

app_name = 'authentication'

urlpatterns = [
    # openid
    path('openid/login/', views.OpenIDLoginView.as_view(), name='openid-login'),
    path('openid/login/complete/',
         views.OpenIDLoginCompleteView.as_view(), name='openid-login-complete'),

    # login
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('login/otp/', views.UserLoginOtpView.as_view(), name='login-otp'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
]
