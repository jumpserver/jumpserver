# coding:utf-8
#

from django.urls import path
from authentication.openid import views

app_name = 'authentication'

urlpatterns = [
    # openid
    path('openid/login/', views.LoginView.as_view(), name='openid-login'),
    path('openid/login/complete/', views.LoginCompleteView.as_view(),
         name='openid-login-complete'),

    # other
]
