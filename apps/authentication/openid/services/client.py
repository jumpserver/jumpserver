# -*- coding: utf-8 -*-
#

from django.conf import settings
from keycloak.keycloak_openid import KeycloakOpenID

from authentication.openid.models import Client


def get_openid_connect_client(client):
    """
    :param authentication.models.Client client:
    :rtype: keycloak.openid_connect.KeycloakOpenidConnect
    """
    openid_connect = client.realm.realm_api_client.open_id_connect(
        client_id=client.client_id,
        client_secret=client.secret
    )
    return openid_connect


def get_openid_client(client):
    """
    :param authentication.models.Client client:
    :rtype: keycloak.keycloak_openid.KeycloakOpenID
    """

    return KeycloakOpenID(
        server_url='%sauth/' % client.realm.server.url,
        realm_name=client.realm.name,
        client_id=client.client_id,
        client_secret_key=client.secret,
    )


def new_client():
    """
    :return: authentication.models.Client
    """
    return Client(
        server_url=settings.AUTH_OPENID_SERVER_URL,
        realm_name=settings.AUTH_OPENID_REALM_NAME,
        client_id=settings.AUTH_OPENID_CLIENT_ID,
        client_secret=settings.AUTH_OPENID_CLIENT_SECRET
    )
