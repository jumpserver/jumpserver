import time

import requests
import requests.exceptions
from django.conf import settings
from django.contrib import auth
from django.core.exceptions import MiddlewareNotUsed

from common.utils import get_logger
from .decorator import ssl_verification
from .utils import validate_and_return_id_token

logger = get_logger(__file__)


class OIDCRefreshIDTokenMiddleware:
    """ Allows to periodically refresh the ID token associated with the authenticated user. """

    def __init__(self, get_response):
        if not settings.AUTH_OPENID:
            raise MiddlewareNotUsed

        self.get_response = get_response

    def __call__(self, request):
        # Refreshes tokens only in the applicable cases.
        if request.method == 'GET' and not self.is_ajax(request) and \
                request.user.is_authenticated and settings.AUTH_OPENID:
            self.refresh_token(request)
        response = self.get_response(request)
        return response

    @staticmethod
    def is_ajax(request):
        return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    @ssl_verification
    def refresh_token(self, request):
        """ Refreshes the token of the current user. """

        log_prompt = "Process refresh Token: {}"
        # logger.debug(log_prompt.format('Start'))

        # NOTE: SHARE_SESSION is False means that the user does not share sessions
        # with other applications
        if not settings.AUTH_OPENID_SHARE_SESSION:
            logger.debug(log_prompt.format('Not share session'))
            return

        # NOTE: no refresh token in the session means that the user wasn't authentified using the
        # OpenID Connect provider (OP).
        refresh_token = request.session.get('oidc_auth_refresh_token')
        if refresh_token is None:
            logger.debug(log_prompt.format('Refresh token is missing'))
            return

        id_token_exp_timestamp = request.session.get('oidc_auth_id_token_exp_timestamp', None)
        now_timestamp = time.time()
        # Returns immediately if the token is still valid.
        if id_token_exp_timestamp is not None and id_token_exp_timestamp > now_timestamp:
            # logger.debug(log_prompt.format('Returns immediately because token is still valid'))
            return

        # Prepares the token payload that will be used to request a new token from the token
        # endpoint.
        refresh_token = request.session.pop('oidc_auth_refresh_token')
        token_payload = {
            'client_id': settings.AUTH_OPENID_CLIENT_ID,
            'client_secret': settings.AUTH_OPENID_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'scope': settings.AUTH_OPENID_SCOPES,
        }

        # Calls the token endpoint.
        logger.debug(log_prompt.format('Calls the token endpoint'))
        token_response = requests.post(settings.AUTH_OPENID_PROVIDER_TOKEN_ENDPOINT, data=token_payload)
        try:
            token_response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.debug(log_prompt.format('Request exception http error: {}'.format(str(e))))
            logger.debug(log_prompt.format('Logout'))
            auth.logout(request)
            return
        token_response_data = token_response.json()

        # Validates the token.
        logger.debug(log_prompt.format('Validate ID Token'))
        raw_id_token = token_response_data.get('id_token')
        id_token = validate_and_return_id_token(raw_id_token, validate_nonce=False)

        # If the token cannot be validated we have to log out the current user.
        if id_token is None:
            logger.debug(log_prompt.format('ID Token is None'))
            auth.logout(request)
            logger.debug(log_prompt.format('Logout'))
            return

        # Retrieves the access token and refresh token.
        access_token = token_response_data.get('access_token')
        refresh_token = token_response_data.get('refresh_token')

        # Stores the ID token, the related access token and the refresh token in the session.
        request.session['oidc_auth_id_token'] = raw_id_token
        request.session['oidc_auth_access_token'] = access_token
        request.session['oidc_auth_refresh_token'] = refresh_token

        # Saves the new expiration timestamp.
        request.session['oidc_auth_id_token_exp_timestamp'] = \
            time.time() + settings.AUTH_OPENID_ID_TOKEN_MAX_AGE
