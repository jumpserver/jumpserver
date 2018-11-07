# -*- coding: utf-8 -*-
#

from django.utils.functional import cached_property

OIDC_ACCESS_TOKEN = 'oidc_access_token'


class Server(object):

    def __init__(self, url):
        self.url = url

    def __str__(self):
        return self.url


class Realm(object):

    def __init__(self, server_url, name):
        self.server = Server(server_url)
        self.name = name

    def __str__(self):
        return self.name

    @cached_property
    def realm_api_client(self):
        """
        :rtype: keycloak.realm.Realm
        """
        import authentication.openid.services.realm
        return authentication.openid.services.realm.get_realm_api_client(realm=self)


class Client(object):

    def __init__(self, server_url, realm_name, client_id, client_secret):
        self.realm = Realm(server_url, realm_name)
        self.client_id = client_id
        self.secret = client_secret
        self._oidc_profile = None

    @property
    def oidc_profile(self):
        return self._oidc_profile

    @oidc_profile.setter
    def oidc_profile(self, profile):
        self._oidc_profile = profile

    @cached_property
    def openid_api_client(self):
        """
        :rtype: keycloak.openid_connect.KeycloakOpenidConnect
        """
        import authentication.openid.services.client
        return authentication.openid.services.client.get_openid_client(self)

    def __str__(self):
        return self.client_id


class OpenIdConnectProfile(object):

    def __init__(self, user, access_token, refresh_token):
        self.user = user
        self.access_token = access_token
        self.refresh_token = refresh_token

    def __str__(self):
        return self.user.username


class Nonce(object):

    def __init__(self, redirect_uri, next_path):
        import uuid
        self.state = uuid.uuid4()
        self.redirect_uri = redirect_uri
        self.next_path = next_path


