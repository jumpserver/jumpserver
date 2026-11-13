# -*- coding: utf-8 -*-
#
from django.urls import path
from django.db import transaction

from . import views
from .agent import AgentAwareAuthorizationView
from .agent_registration import AgentClientRegistrationView
from .client_views import ClientTokenView, ClientRevokeTokenView


urlpatterns = [
    path("register/", transaction.non_atomic_requests(AgentClientRegistrationView.as_view()), name="agent-register"),
    path("authorize/", AgentAwareAuthorizationView.as_view(), name="authorize"),
    path("token/", ClientTokenView.as_view(), name="token"),
    path("revoke/", ClientRevokeTokenView.as_view(), name="revoke-token"),
    path(".well-known/oauth-authorization-server", views.OAuthAuthorizationServerView.as_view(), name="oauth-authorization-server"),
]
