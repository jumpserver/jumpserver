# -*- coding: utf-8 -*-
#
from django.urls import path
from django.db import transaction

from authentication.backends.oauth2_provider.agent import AgentAwareAuthorizationView
from authentication.backends.oauth2_provider.agent_registration import AgentClientRegistrationView
from authentication.backends.oauth2_provider.client_views import (
    ClientTokenView, ClientRevokeTokenView,
)

from . import views


urlpatterns = [
    path(
        "register/",
        transaction.non_atomic_requests(AgentClientRegistrationView.as_view()),
        name="agent-register",
    ),
    path("authorize/", AgentAwareAuthorizationView.as_view(), name="authorize"),
    path("token/", ClientTokenView.as_view(), name="token"),
    path("revoke/", ClientRevokeTokenView.as_view(), name="revoke-token"),
    path(
        ".well-known/oauth-authorization-server",
        views.OAuthAuthorizationServerView.as_view(),
        name="oauth-authorization-server",
    ),
]
