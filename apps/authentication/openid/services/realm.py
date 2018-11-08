# -*- coding: utf-8 -*-
#

from keycloak.realm import KeycloakRealm


def get_realm_api_client(realm):
    """
    :param authentication.openid.models.Realm realm:
    :return keycloak.realm.Realm:
    """
    return KeycloakRealm(
        server_url=realm.server.url,
        realm_name=realm.name,
        headers={}
    )
