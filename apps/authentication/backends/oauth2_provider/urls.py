# -*- coding: utf-8 -*-
#
from django.urls import path

from . import views
from .client_views import ClientAuthorizationView, ClientTokenView, ClientRevokeTokenView


urlpatterns = [
    path("authorize/", ClientAuthorizationView.as_view(), name="authorize"),
    path("token/", ClientTokenView.as_view(), name="token"),
    path("revoke/", ClientRevokeTokenView.as_view(), name="revoke-token"),
    path(".well-known/oauth-authorization-server", views.OAuthAuthorizationServerView.as_view(), name="oauth-authorization-server"),
]
