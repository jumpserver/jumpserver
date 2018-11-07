# -*- coding: utf-8 -*-
#

from keycloak.realm import KeycloakRealm


def get_realm_api_client(realm):
    """
    :param authentication.openid.models.Realm realm:
    :return keycloak.realm.Realm:
    """
    headers = {}
    server_url = realm.server.url
    return KeycloakRealm(
        server_url=server_url, realm_name=realm.name, headers=headers
    )
