# -*- coding: utf-8 -*-
#
from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.OpenIDLoginView.as_view(), name='openid-login'),
    path('login/complete/', views.OpenIDLoginCompleteView.as_view(),
         name='openid-login-complete'),
]
