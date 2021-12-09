# -*- coding: utf-8 -*-
#
from django.urls import path

from . import views


urlpatterns = [
    path('login/', views.Saml2AuthRequestView.as_view(), name='saml2-login'),
    path('logout/', views.Saml2EndSessionView.as_view(), name='saml2-logout'),
    path('callback/', views.Saml2AuthCallbackView.as_view(), name='saml2-callback'),
    path('metadata/', views.Saml2AuthMetadataView.as_view(), name='saml2-metadata'),
]
