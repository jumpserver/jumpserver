# -*- coding: utf-8 -*-
# @Time    : 2019/11/22 1:50 下午
# @Author  : Alex
# @Email   : 1374462869@qq.com
# @Project : jumpserver
# @File    : urls.py

from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.OIDCAuthRequestView.as_view(), name='openid-login'),
    path('login/complete/', views.OIDCAuthCallbackView.as_view(),
         name='openid-login-complete'),
]
