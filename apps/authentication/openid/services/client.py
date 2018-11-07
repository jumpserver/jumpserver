# -*- coding: utf-8 -*-
#

from ..models import Client
from django.conf import settings


def get_openid_client(client):
    """
    :param authentication.models.Client client:
    :rtype: keycloak.openid_connect.KeycloakOpenidConnect
    """
    openid = client.realm.realm_api_client.open_id_connect(
        client_id=client.client_id,
        client_secret=client.secret
    )
    return openid


def new_client():
    _client = Client(
        server_url=settings.AUTH_OPENID_SERVER_URL,
        realm_name=settings.AUTH_OPENID_REALM_NAME,
        client_id=settings.AUTH_OPENID_CLIENT_ID,
        client_secret=settings.AUTH_OPENID_CLIENT_SECRET
    )
    return _client
