import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import SuspiciousOperation
from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils.module_loading import import_string

from oidc_rp.conf import settings as oidc_rp_settings
from oidc_rp.models import OIDCUser
from oidc_rp.signals import oidc_user_created
from oidc_rp.backends import OIDCAuthBackend
from oidc_rp.utils import validate_and_return_id_token


__all__ = ['OIDCAuthCodeBackend', 'OIDCAuthPasswordBackend']


class OIDCAuthCodeBackend(OIDCAuthBackend):
    def authenticate(self, request, nonce=None, **kwargs):
        """ Authenticates users in case of the OpenID Connect Authorization code flow. """
        # NOTE: the request object is mandatory to perform the authentication using an authorization
        # code provided by the OIDC supplier.
        if (nonce is None and oidc_rp_settings.USE_NONCE) or request is None:
            return

        # Fetches required GET parameters from the HTTP request object.
        state = request.GET.get('state')
        code = request.GET.get('code')

        # Don't go further if the state value or the authorization code is not present in the GET
        # parameters because we won't be able to get a valid token for the user in that case.
        if (state is None and oidc_rp_settings.USE_STATE) or code is None:
            raise SuspiciousOperation('Authorization code or state value is missing')

        # Prepares the token payload that will be used to request an authentication token to the
        # token endpoint of the OIDC provider.
        token_payload = {
            'client_id': oidc_rp_settings.CLIENT_ID,
            'client_secret': oidc_rp_settings.CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': request.build_absolute_uri(
                reverse(settings.OIDC_RP_LOGIN_CALLBACK_URL_NAME)
            ),
        }

        # Calls the token endpoint.
        token_response = requests.post(oidc_rp_settings.PROVIDER_TOKEN_ENDPOINT, data=token_payload)
        token_response.raise_for_status()
        token_response_data = token_response.json()

        # Validates the token.
        raw_id_token = token_response_data.get('id_token')
        id_token = validate_and_return_id_token(raw_id_token, nonce)
        if id_token is None:
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
        if oidc_rp_settings.ID_TOKEN_INCLUDE_USERINFO:
            userinfo_data = id_token
        else:
            # Fetches the user information from the userinfo endpoint provided by the OP.
            userinfo_response = requests.get(
                oidc_rp_settings.PROVIDER_USERINFO_ENDPOINT,
                headers={'Authorization': 'Bearer {0}'.format(access_token)})
            userinfo_response.raise_for_status()
            userinfo_data = userinfo_response.json()

        # Tries to retrieve a corresponding user in the local database and creates it if applicable.
        try:
            oidc_user = OIDCUser.objects.select_related('user').get(sub=userinfo_data.get('sub'))
        except OIDCUser.DoesNotExist:
            oidc_user = create_oidc_user_from_claims(userinfo_data)
            oidc_user_created.send(sender=self.__class__, request=request, oidc_user=oidc_user)
        else:
            update_oidc_user_from_claims(oidc_user, userinfo_data)

        # Runs a custom user details handler if applicable. Such handler could be responsible for
        # creating / updating whatever is necessary to manage the considered user (eg. a profile).
        user_details_handler(oidc_user, userinfo_data)

        return oidc_user.user


class OIDCAuthPasswordBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):

        if username is None and password is None:
            return

        # Prepares the token payload that will be used to request an authentication token to the
        # token endpoint of the OIDC provider.
        token_payload = {
            'client_id': oidc_rp_settings.CLIENT_ID,
            'client_secret': oidc_rp_settings.CLIENT_SECRET,
            'grant_type': 'password',
            'username': username,
            'password': password,
        }

        token_response = requests.post(oidc_rp_settings.PROVIDER_TOKEN_ENDPOINT, data=token_payload)
        token_response.raise_for_status()
        token_response_data = token_response.json()

        access_token = token_response_data.get('access_token')

        # Fetches the user information from the userinfo endpoint provided by the OP.
        userinfo_response = requests.get(
            oidc_rp_settings.PROVIDER_USERINFO_ENDPOINT,
            headers={'Authorization': 'Bearer {0}'.format(access_token)})
        userinfo_response.raise_for_status()
        userinfo_data = userinfo_response.json()

        # Tries to retrieve a corresponding user in the local database and creates it if applicable.
        try:
            oidc_user = OIDCUser.objects.select_related('user').get(sub=userinfo_data.get('sub'))
        except OIDCUser.DoesNotExist:
            oidc_user = create_oidc_user_from_claims(userinfo_data)
            oidc_user_created.send(sender=self.__class__, request=request, oidc_user=oidc_user)
        else:
            update_oidc_user_from_claims(oidc_user, userinfo_data)

        # Runs a custom user details handler if applicable. Such handler could be responsible for
        # creating / updating whatever is necessary to manage the considered user (eg. a profile).
        user_details_handler(oidc_user, userinfo_data)

        return oidc_user.user


def get_or_create_user(username, email):
    user, created = get_user_model().objects.get_or_create(username=username)
    return user


@transaction.atomic
def create_oidc_user_from_claims(claims):
    """
    Creates an ``OIDCUser`` instance using the claims extracted
    from an id_token.
    """
    sub = claims['sub']
    email = claims.get('email')
    username = claims.get('preferred_username')
    user = get_or_create_user(username, email)
    oidc_user = OIDCUser.objects.create(user=user, sub=sub, userinfo=claims)

    return oidc_user


@transaction.atomic
def update_oidc_user_from_claims(oidc_user, claims):
    """
    Updates an ``OIDCUser`` instance using the claims extracted
    from an id_token.
    """
    oidc_user.userinfo = claims
    oidc_user.save()


@transaction.atomic
def user_details_handler(oidc_user, userinfo_data):
    name = userinfo_data.get('name')
    username = userinfo_data.get('preferred_username')
    email = userinfo_data.get('email')
    oidc_user.user.name = name or username
    oidc_user.user.username = username
    oidc_user.user.email = email
    oidc_user.user.save()
