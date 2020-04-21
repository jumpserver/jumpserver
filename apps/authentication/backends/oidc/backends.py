import requests
from django.utils.module_loading import import_string
from django.contrib.auth.backends import ModelBackend
from oidc_rp.conf import settings as oidc_rp_settings
from oidc_rp.models import OIDCUser
from oidc_rp.signals import oidc_user_created
from oidc_rp.backends import (
    create_oidc_user_from_claims, update_oidc_user_from_claims,
)


__all__ = ['OIDCAuthPasswordBackend']


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
        user_details_handler = import_string(oidc_rp_settings.USER_DETAILS_HANDLER) \
            if oidc_rp_settings.USER_DETAILS_HANDLER is not None else None
        if user_details_handler is not None:
            user_details_handler(oidc_user, userinfo_data)

        return oidc_user.user


