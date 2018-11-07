# -*- coding: utf-8 -*-
#

from django.contrib.auth import get_user_model
from django.db import transaction

from ..models import OpenIdConnectProfile


def update_or_create_from_code(code, client, redirect_uri):
    """
    Update or create an user based on an authentication code.
    Response as specified in:

    https://tools.ietf.org/html/rfc6749#section-4.1.4

    :param authentication.openid.models.Client client:
    :param str code: authentication code
    :param str redirect_uri:
    :rtype: authentication.models.OpenIdConnectProfile
    """

    token_response = client.openid_api_client.authorization_code(
        code=code, redirect_uri=redirect_uri)

    return _update_or_create(client=client, token_response=token_response)


def _update_or_create(client, token_response):
    """
    Update or create an user based on a token response.

    `token_response` contains the items returned by the OpenIDConnect Token API
    end-point:
     - id_token
     - access_token
     - expires_in
     - refresh_token
     - refresh_expires_in

    :param authentication.openid.models.Client client:
    :param dict token_response:
    :rtype: authentication.openid.models.OpenIdConnectProfile
    """

    userinfo = client.openid_api_client.userinfo(
        token=token_response['access_token'])

    with transaction.atomic():
        user, _ = get_user_model().objects.update_or_create(
            username=userinfo.get('preferred_username', ''),
            defaults={
                'email': userinfo.get('email', ''),
                'first_name': userinfo.get('given_name', ''),
                'last_name': userinfo.get('family_name', '')
            }
        )

        oidc_profile = OpenIdConnectProfile(
            user=user,
            access_token=token_response['access_token'],
            refresh_token=token_response['refresh_token'],
        )
        client.oidc_profile = oidc_profile

    return oidc_profile
