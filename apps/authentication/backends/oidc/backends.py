"""
    OpenID Connect relying party (RP) authentication backends
    =========================================================

    This modules defines backends allowing to authenticate a user using a specific token endpoint
    of an OpenID Connect provider (OP).

"""

import base64
import requests

from rest_framework.exceptions import ParseError
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.urls import reverse
from django.conf import settings

from common.utils import get_logger
from authentication.utils import build_absolute_uri_for_oidc
from users.utils import construct_user_email

from ..base import JMSBaseAuthBackend
from .utils import validate_and_return_id_token
from .decorator import ssl_verification
from .signals import (
    openid_create_or_update_user
)
from authentication.signals import user_auth_success, user_auth_failed

logger = get_logger(__file__)

__all__ = ['OIDCAuthCodeBackend', 'OIDCAuthPasswordBackend']


class UserMixin:

    @transaction.atomic
    def get_or_create_user_from_claims(self, request, claims):
        log_prompt = "Get or Create user from claims [ActionForUser]: {}"
        logger.debug(log_prompt.format('start'))

        sub = claims['sub']

        # Construct user attrs value
        user_attrs = {}
        for field, attr in settings.AUTH_OPENID_USER_ATTR_MAP.items():
            user_attrs[field] = claims.get(attr, sub)
        email = user_attrs.get('email', '')
        email = construct_user_email(user_attrs.get('username'), email)
        user_attrs.update({'email': email})

        logger.debug(log_prompt.format(user_attrs))

        username = user_attrs.get('username')
        name = user_attrs.get('name')

        user, created = get_user_model().objects.get_or_create(
            username=username, defaults=user_attrs
        )
        logger.debug(log_prompt.format("user: {}|created: {}".format(user, created)))
        logger.debug(log_prompt.format("Send signal => openid create or update user"))
        openid_create_or_update_user.send(
            sender=self.__class__, request=request, user=user, created=created,
            name=name, username=username, email=email
        )
        return user, created


class OIDCBaseBackend(UserMixin, JMSBaseAuthBackend, ModelBackend):

    @staticmethod
    def is_enabled():
        return settings.AUTH_OPENID


class OIDCAuthCodeBackend(OIDCBaseBackend):
    """ Allows to authenticate users using an OpenID Connect Provider (OP).

    This authentication backend is able to authenticate users in the case of the OpenID Connect
    Authorization Code flow. The ``authenticate`` method provided by this backend is likely to be
    called when the callback URL is requested by the OpenID Connect Provider (OP). Thus it will
    call the OIDC provider again in order to request a valid token using the authorization code that
    should be available in the request parameters associated with the callback call.

    """

    @ssl_verification
    def authenticate(self, request, nonce=None, code_verifier=None, **kwargs):
        """ Authenticates users in case of the OpenID Connect Authorization code flow. """
        log_prompt = "Process authenticate [OIDCAuthCodeBackend]: {}"
        logger.debug(log_prompt.format('start'))

        # NOTE: the request object is mandatory to perform the authentication using an authorization
        # code provided by the OIDC supplier.
        if (nonce is None and settings.AUTH_OPENID_USE_NONCE) or request is None:
            logger.debug(log_prompt.format('Request or nonce value is missing'))
            return

        # Fetches required GET parameters from the HTTP request object.
        state = request.GET.get('state')
        code = request.GET.get('code')

        # Don't go further if the state value or the authorization code is not present in the GET
        # parameters because we won't be able to get a valid token for the user in that case.
        if (state is None and settings.AUTH_OPENID_USE_STATE) or code is None:
            logger.debug(log_prompt.format('Authorization code or state value is missing'))
            raise SuspiciousOperation('Authorization code or state value is missing')

        # Prepares the token payload that will be used to request an authentication token to the
        # token endpoint of the OIDC provider.
        logger.debug(log_prompt.format('Prepares token payload'))
        """ 
        The reason for need not client_id and client_secret in token_payload.
        OIDC protocol indicate client's token_endpoint_auth_method only accept one type in
            - client_secret_basic
            - client_secret_post
            - client_secret_jwt
            - private_key_jwt
            - none
        If the client offer more than one auth method type to OIDC, OIDC will auth client failed.
        OIDC default use client_secret_basic, 
        this type only need in headers add Authorization=Basic xxx.
        
        More info see: https://github.com/jumpserver/jumpserver/issues/8165
        More info see: https://openid.net/specs/openid-connect-core-1_0.html#ClientAuthentication
        """
        token_payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': build_absolute_uri_for_oidc(
                request, path=reverse(settings.AUTH_OPENID_AUTH_LOGIN_CALLBACK_URL_NAME)
            )
        }
        if settings.AUTH_OPENID_PKCE and code_verifier:
            token_payload['code_verifier'] = code_verifier
        if settings.AUTH_OPENID_CLIENT_AUTH_METHOD == 'client_secret_post':
            token_payload.update({
                'client_id': settings.AUTH_OPENID_CLIENT_ID,
                'client_secret': settings.AUTH_OPENID_CLIENT_SECRET,
            })
            headers = None
        else:
            # Prepares the token headers that will be used to request an authentication token to the
            # token endpoint of the OIDC provider.
            logger.debug(log_prompt.format('Prepares token headers'))
            basic_token = "{}:{}".format(
                settings.AUTH_OPENID_CLIENT_ID, settings.AUTH_OPENID_CLIENT_SECRET
            )
            headers = {
                "Authorization": "Basic {}".format(base64.b64encode(basic_token.encode()).decode())
            }

        # Calls the token endpoint.
        logger.debug(log_prompt.format('Call the token endpoint'))
        token_response = requests.post(
            settings.AUTH_OPENID_PROVIDER_TOKEN_ENDPOINT, data=token_payload, headers=headers
        )
        try:
            token_response.raise_for_status()
            token_response_data = token_response.json()
        except Exception as e:
            error = "Json token response error, token response " \
                    "content is: {}, error is: {}".format(token_response.content, str(e))
            logger.debug(log_prompt.format(error))
            raise ParseError(error)

        # Validates the token.
        logger.debug(log_prompt.format('Validate ID Token'))
        raw_id_token = token_response_data.get('id_token')
        id_token = validate_and_return_id_token(raw_id_token, nonce)
        if id_token is None:
            logger.debug(log_prompt.format(
                'ID Token is missing, raw id token is: {}'.format(raw_id_token))
            )
            return

        # Retrieves the access token and refresh token.
        access_token = token_response_data.get('access_token')
        refresh_token = token_response_data.get('refresh_token')

        # Stores the ID token, the related access token and the refresh token in the session.
        request.session['oidc_auth_id_token'] = raw_id_token
        request.session['oidc_auth_access_token'] = access_token
        request.session['oidc_auth_refresh_token'] = refresh_token

        # If the id_token contains userinfo scopes and claims we don't have to hit the userinfo
        # endpoint.
        # https://openid.net/specs/openid-connect-core-1_0.html#StandardClaims
        if settings.AUTH_OPENID_ID_TOKEN_INCLUDE_CLAIMS:
            logger.debug(log_prompt.format('ID Token in claims'))
            claims = id_token
        else:
            # Fetches the claims (user information) from the userinfo endpoint provided by the OP.
            logger.debug(log_prompt.format('Fetches the claims from the userinfo endpoint'))
            claims_response = requests.get(
                settings.AUTH_OPENID_PROVIDER_USERINFO_ENDPOINT,
                headers={'Authorization': 'Bearer {0}'.format(access_token)}
            )
            try:
                claims_response.raise_for_status()
                claims = claims_response.json()
            except Exception as e:
                error = "Json claims response error, claims response " \
                        "content is: {}, error is: {}".format(claims_response.content, str(e))
                logger.debug(log_prompt.format(error))
                raise ParseError(error)

        logger.debug(log_prompt.format('Get or create user from claims'))
        user, created = self.get_or_create_user_from_claims(request, claims)

        logger.debug(log_prompt.format('Update or create oidc user'))

        if self.user_can_authenticate(user):
            logger.debug(log_prompt.format('OpenID user login success'))
            logger.debug(log_prompt.format('Send signal => openid user login success'))
            user_auth_success.send(
                sender=self.__class__, request=request, user=user,
                backend=settings.AUTH_BACKEND_OIDC_CODE
            )
            return user
        else:
            logger.debug(log_prompt.format('OpenID user login failed'))
            logger.debug(log_prompt.format('Send signal => openid user login failed'))
            user_auth_failed.send(
                sender=self.__class__, request=request, username=user.username,
                reason="User is invalid", backend=settings.AUTH_BACKEND_OIDC_CODE

            )
            return None


class OIDCAuthPasswordBackend(OIDCBaseBackend):

    @ssl_verification
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            return self._authenticate(request, username, password, **kwargs)
        except Exception as e:
            error = f'Authenticate exception: {e}'
            logger.error(error, exc_info=True)
            return

    def _authenticate(self, request, username=None, password=None, **kwargs):
        """
        https://oauth.net/2/
        https://aaronparecki.com/oauth-2-simplified/#password
        """
        log_prompt = "Process authenticate [OIDCAuthPasswordBackend]: {}"
        logger.debug(log_prompt.format('start'))
        request_timeout = 15

        if not username or not password:
            logger.debug(log_prompt.format('Username or password is missing'))
            return

        # Prepares the token payload that will be used to request an authentication token to the
        # token endpoint of the OIDC provider.
        logger.debug(log_prompt.format('Prepares token payload'))
        token_payload = {
            'client_id': settings.AUTH_OPENID_CLIENT_ID,
            'client_secret': settings.AUTH_OPENID_CLIENT_SECRET,
            'grant_type': 'password',
            'username': username,
            'password': password,
        }

        # Calls the token endpoint.
        logger.debug(log_prompt.format('Call the token endpoint'))
        token_response = requests.post(settings.AUTH_OPENID_PROVIDER_TOKEN_ENDPOINT, data=token_payload, timeout=request_timeout)
        try:
            token_response.raise_for_status()
            token_response_data = token_response.json()
        except Exception as e:
            error = "Json token response error, token response " \
                    "content is: {}, error is: {}".format(token_response.content, str(e))
            logger.debug(log_prompt.format(error))
            logger.debug(log_prompt.format('Send signal => openid user login failed'))
            user_auth_failed.send(
                sender=self.__class__, request=request, username=username, reason=error,
                backend=settings.AUTH_BACKEND_OIDC_PASSWORD
            )
            return

        # Retrieves the access token
        access_token = token_response_data.get('access_token')

        # Fetches the claims (user information) from the userinfo endpoint provided by the OP.
        logger.debug(log_prompt.format('Fetches the claims from the userinfo endpoint'))
        claims_response = requests.get(
            settings.AUTH_OPENID_PROVIDER_USERINFO_ENDPOINT,
            headers={'Authorization': 'Bearer {0}'.format(access_token)},
            timeout=request_timeout
        )
        try:
            claims_response.raise_for_status()
            claims = claims_response.json()
            preferred_username = claims.get('preferred_username')
            if preferred_username and \
                    preferred_username.lower() == username.lower() and \
                    preferred_username != username:
                return
        except Exception as e:
            error = "Json claims response error, claims response " \
                    "content is: {}, error is: {}".format(claims_response.content, str(e))
            logger.debug(log_prompt.format(error))
            logger.debug(log_prompt.format('Send signal => openid user login failed'))
            user_auth_failed.send(
                sender=self.__class__, request=request, username=username, reason=error,
                backend=settings.AUTH_BACKEND_OIDC_PASSWORD
            )
            return

        logger.debug(log_prompt.format('Get or create user from claims'))
        user, created = self.get_or_create_user_from_claims(request, claims)

        logger.debug(log_prompt.format('Update or create oidc user'))

        if self.user_can_authenticate(user):
            logger.debug(log_prompt.format('OpenID user login success'))
            logger.debug(log_prompt.format('Send signal => openid user login success'))
            user_auth_success.send(
                sender=self.__class__, request=request, user=user,
                backend=settings.AUTH_BACKEND_OIDC_PASSWORD
            )
            return user
        else:
            logger.debug(log_prompt.format('OpenID user login failed'))
            logger.debug(log_prompt.format('Send signal => openid user login failed'))
            user_auth_failed.send(
                sender=self.__class__, request=request, username=username, reason="User is invalid",
                backend=settings.AUTH_BACKEND_OIDC_PASSWORD
            )
            return None
