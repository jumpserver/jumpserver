# -*- coding: utf-8 -*-
#
from django.urls import path

from oauth2_provider import views as op_views
from . import views
from .client_views import ClientAuthorizationView


urlpatterns = [
    path("authorize/", ClientAuthorizationView.as_view(), name="authorize"),
    path("token/", op_views.TokenView.as_view(), name="token"),
    path("revoke/", op_views.RevokeTokenView.as_view(), name="revoke-token"),
    path(".well-known/oauth-authorization-server", views.OAuthAuthorizationServerView.as_view(), name="oauth-authorization-server"),
]
