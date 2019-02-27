# coding:utf-8
#

from django.urls import path
from .. import views

app_name = 'authentication'

urlpatterns = [
    # openid
    path('openid/login/', views.OpenIDLoginView.as_view(), name='openid-login'),
    path('openid/login/complete/', views.OpenIDLoginCompleteView.as_view(),
         name='openid-login-complete'),
]
