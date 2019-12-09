# -*- coding: utf-8 -*-
#

from django.db import transaction
from django.contrib.auth import get_user_model
from keycloak.realm import KeycloakRealm
from keycloak.keycloak_openid import KeycloakOpenID

from .signals import post_create_or_update_openid_user
from .decorator import ssl_verification

OIDT_ACCESS_TOKEN = 'oidt_access_token'


class Nonce(object):
    """
    The openid-login is stored in cache as a temporary object, recording the
    user's redirect_uri and next_pat
    """
    def __init__(self, redirect_uri, next_path):
        import uuid
        self.state = uuid.uuid4()
        self.redirect_uri = redirect_uri
        self.next_path = next_path


class OpenIDTokenProfile(object):
    def __init__(self, user, access_token, refresh_token):
        """
        :param user: User object
        :param access_token:
        :param refresh_token:
        """
        self.user = user
        self.access_token = access_token
        self.refresh_token = refresh_token

    def __str__(self):
        return "{}'s OpenID token profile".format(self.user.username)


class Client(object):
    def __init__(self, server_url, realm_name, client_id, client_secret):
        self.server_url = server_url
        self.realm_name = realm_name
        self.client_id = client_id
        self.client_secret = client_secret
        self._openid_client = None
        self._realm = None
        self._openid_connect_client = None

    @property
    def realm(self):
        if self._realm is None:
            self._realm = KeycloakRealm(
                server_url=self.server_url,
                realm_name=self.realm_name,
                headers={}
            )
        return self._realm

    @property
    def openid_connect_client(self):
        """
        :rtype: keycloak.openid_connect.KeycloakOpenidConnect
        """
        if self._openid_connect_client is None:
            self._openid_connect_client = self.realm.open_id_connect(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
        return self._openid_connect_client

    @property
    def openid_client(self):
        """
        :rtype: keycloak.keycloak_openid.KeycloakOpenID
        """
        if self._openid_client is None:
            self._openid_client = KeycloakOpenID(
                server_url='%sauth/' % self.server_url,
                realm_name=self.realm_name,
                client_id=self.client_id,
                client_secret_key=self.client_secret,
            )
        return self._openid_client

    @ssl_verification
    def get_url(self, name):
        return self.openid_connect_client.get_url(name=name)

    def get_url_end_session_endpoint(self):
        return self.get_url(name='end_session_endpoint')

    @ssl_verification
    def get_authorization_url(self, redirect_uri, scope, state):
        url = self.openid_connect_client.authorization_url(
            redirect_uri=redirect_uri, scope=scope, state=state
        )
        return url

    @ssl_verification
    def get_userinfo(self, token):
        user_info = self.openid_connect_client.userinfo(token=token)
        return user_info

    @ssl_verification
    def authorization_code(self, code, redirect_uri):
        token_response = self.openid_connect_client.authorization_code(
            code=code, redirect_uri=redirect_uri
        )
        return token_response

    @ssl_verification
    def authorization_password(self, username, password):
        token_response = self.openid_client.token(
            username=username, password=password
        )
        return token_response

    def update_or_create_from_code(self, code, redirect_uri):
        """
        Update or create an user based on an authentication code.
        Response as specified in:
        https://tools.ietf.org/html/rfc6749#section-4.1.4
        :param str code: authentication code
        :param str redirect_uri:
        :rtype: OpenIDTokenProfile
        """
        token_response = self.authorization_code(code, redirect_uri)
        return self._update_or_create(token_response=token_response)

    def update_or_create_from_password(self, username, password):
        """
        Update or create an user based on an authentication username and password.
        :param str username: authentication username
        :param str password: authentication password
        :return: OpenIDTokenProfile
        """
        token_response = self.authorization_password(username, password)
        return self._update_or_create(token_response=token_response)

    def _update_or_create(self, token_response):
        """
        Update or create an user based on a token response.
        `token_response` contains the items returned by the OpenIDConnect Token API
        end-point:
         - id_token
         - access_token
         - expires_in
         - refresh_token
         - refresh_expires_in
        :param dict token_response:
        :rtype: OpenIDTokenProfile
        """
        userinfo = self.get_userinfo(token=token_response['access_token'])
        with transaction.atomic():
            user, created = get_user_model().objects.update_or_create(
                username=userinfo.get('preferred_username', ''),
                defaults={
                    'email': userinfo.get('email', ''),
                    'first_name': userinfo.get('given_name', ''),
                    'last_name': userinfo.get('family_name', '')
                }
            )
            oidt_profile = OpenIDTokenProfile(
                user=user,
                access_token=token_response['access_token'],
                refresh_token=token_response['refresh_token'],
            )
            if user:
                post_create_or_update_openid_user.send(
                    sender=user.__class__, user=user, created=created
                )

        return oidt_profile

    def __str__(self):
        return self.client_id
