# -*- coding: utf-8 -*-
#
import django_cas_ng.views
from django.urls import path

from .views import CASLoginView

urlpatterns = [
    path('login/', CASLoginView.as_view(), name='cas-login'),
    path('logout/', django_cas_ng.views.LogoutView.as_view(), name='cas-logout'),
    path('callback/', django_cas_ng.views.CallbackView.as_view(), name='cas-proxy-callback')
]
