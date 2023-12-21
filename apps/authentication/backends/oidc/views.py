"""
    OpenID Connect relying party (RP) views
    =======================================

    This modules defines views allowing to start the authorization and authentication process in
    order to authenticate a specific user. The most important views are: the "login" allowing to
    authenticate the users using the OP and get an authorizartion code, the callback view allowing
    to retrieve a valid token for the considered user and the logout view.

"""

import base64
import hashlib
import secrets
import time

from django.conf import settings
from django.contrib import auth
from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponseRedirect, QueryDict
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.http import urlencode
from django.views.generic import View

from authentication.utils import build_absolute_uri_for_oidc
from common.utils import safe_next_url
from .utils import get_logger

logger = get_logger(__file__)


class OIDCAuthRequestView(View):
    """ Allows to start the authorization flow in order to authenticate the end-user.

    This view acts as the main endpoint to trigger the authentication process involving the OIDC
    provider (OP). It prepares an authentication request that will be sent to the authorization
    server in order to authenticate the end-user.

    """

    http_method_names = ['get', ]

    @staticmethod
    def gen_code_verifier(length=128):
        # length range 43 ~ 128
        return secrets.token_urlsafe(length - 32)

    @staticmethod
    def gen_code_challenge(code_verifier, code_challenge_method):
        if code_challenge_method == 'plain':
            return code_verifier
        h = hashlib.sha256(code_verifier.encode('ascii')).digest()
        b = base64.urlsafe_b64encode(h)
        return b.decode('ascii')[:-1]

    def get(self, request):
        """ Processes GET requests. """

        log_prompt = "Process GET requests [OIDCAuthRequestView]: {}"
        logger.debug(log_prompt.format('Start'))

        # Defines common parameters used to bootstrap the authentication request.
        logger.debug(log_prompt.format('Construct request params'))
        authentication_request_params = request.GET.dict()
        authentication_request_params.update({
            'scope': settings.AUTH_OPENID_SCOPES,
            'response_type': 'code',
            'client_id': settings.AUTH_OPENID_CLIENT_ID,
            'redirect_uri': build_absolute_uri_for_oidc(
                request, path=reverse(settings.AUTH_OPENID_AUTH_LOGIN_CALLBACK_URL_NAME)
            )
        })

        if settings.AUTH_OPENID_PKCE:
            code_verifier = self.gen_code_verifier()
            code_challenge_method = settings.AUTH_OPENID_CODE_CHALLENGE_METHOD or 'S256'
            code_challenge = self.gen_code_challenge(code_verifier, code_challenge_method)
            authentication_request_params.update({
                'code_challenge_method': code_challenge_method,
                'code_challenge': code_challenge
            })
            request.session['oidc_auth_code_verifier'] = code_verifier

        # States should be used! They are recommended in order to maintain state between the
        # authentication request and the callback.
        if settings.AUTH_OPENID_USE_STATE:
            logger.debug(log_prompt.format('Use state'))
            state = get_random_string(settings.AUTH_OPENID_STATE_LENGTH)
            authentication_request_params.update({'state': state})
            request.session['oidc_auth_state'] = state

        # Nonces should be used too! In that case the generated nonce is stored both in the
        # authentication request parameters and in the user's session.
        if settings.AUTH_OPENID_USE_NONCE:
            logger.debug(log_prompt.format('Use nonce'))
            nonce = get_random_string(settings.AUTH_OPENID_NONCE_LENGTH)
            authentication_request_params.update({'nonce': nonce, })
            request.session['oidc_auth_nonce'] = nonce

        # Stores the "next" URL in the session if applicable.
        logger.debug(log_prompt.format('Stores next url in the session'))
        next_url = request.GET.get('next')
        request.session['oidc_auth_next_url'] = safe_next_url(next_url, request=request)

        # Redirects the user to authorization endpoint.
        logger.debug(log_prompt.format('Construct redirect url'))
        query = urlencode(authentication_request_params)
        redirect_url = '{url}?{query}'.format(
            url=settings.AUTH_OPENID_PROVIDER_AUTHORIZATION_ENDPOINT, query=query)

        logger.debug(log_prompt.format('Redirect'))
        return HttpResponseRedirect(redirect_url)


class OIDCAuthCallbackView(View):
    """ Allows to complete the authentication process.

    This view acts as the main endpoint to complete the authentication process involving the OIDC
    provider (OP). It checks the request sent by the OIDC provider in order to determine whether the
    considered was successfully authentified or not and authenticates the user at the current
    application level if applicable.

    """

    http_method_names = ['get', ]

    def get(self, request):
        """ Processes GET requests. """
        log_prompt = "Process GET requests [OIDCAuthCallbackView]: {}"
        logger.debug(log_prompt.format('Start'))
        callback_params = request.GET

        # Retrieve the state value that was previously generated. No state means that we cannot
        # authenticate the user (so a failure should be returned).
        state = request.session.get('oidc_auth_state', None)

        # Retrieve the nonce that was previously generated and remove it from the current session.
        # If no nonce is available (while the USE_NONCE setting is set to True) this means that the
        # authentication cannot be performed and so we have redirect the user to a failure URL.
        nonce = request.session.pop('oidc_auth_nonce', None)

        # NOTE: a redirect to the failure page should be return if some required GET parameters are
        # missing or if no state can be retrieved from the current session.

        if (
                ((nonce and settings.AUTH_OPENID_USE_NONCE) or not settings.AUTH_OPENID_USE_NONCE)
                and
                (
                        (state and settings.AUTH_OPENID_USE_STATE and 'state' in callback_params)
                        or
                        (not settings.AUTH_OPENID_USE_STATE)
                )
                and
                ('code' in callback_params)
        ):
            # Ensures that the passed state values is the same as the one that was previously
            # generated when forging the authorization request. This is necessary to mitigate
            # Cross-Site Request Forgery (CSRF, XSRF).
            if settings.AUTH_OPENID_USE_STATE and callback_params['state'] != state:
                logger.debug(log_prompt.format('Invalid OpenID Connect callback state value'))
                raise SuspiciousOperation('Invalid OpenID Connect callback state value')

            # Authenticates the end-user.
            next_url = request.session.get('oidc_auth_next_url', None)
            code_verifier = request.session.get('oidc_auth_code_verifier', None)
            logger.debug(log_prompt.format('Process authenticate'))
            user = auth.authenticate(nonce=nonce, request=request, code_verifier=code_verifier)
            if user:
                logger.debug(log_prompt.format('Login: {}'.format(user)))
                auth.login(self.request, user)
                # Stores an expiration timestamp in the user's session. This value will be used if
                # the project is configured to periodically refresh user's token.
                self.request.session['oidc_auth_id_token_exp_timestamp'] = \
                    time.time() + settings.AUTH_OPENID_ID_TOKEN_MAX_AGE
                # Stores the "session_state" value that can be passed by the OpenID Connect provider
                # in order to maintain a consistent session state across the OP and the related
                # relying parties (RP).
                self.request.session['oidc_auth_session_state'] = \
                    callback_params.get('session_state', None)

                logger.debug(log_prompt.format('Redirect'))
                return HttpResponseRedirect(
                    next_url or settings.AUTH_OPENID_AUTHENTICATION_REDIRECT_URI
                )

        if 'error' in callback_params:
            logger.debug(
                log_prompt.format('Error in callback params: {}'.format(callback_params['error']))
            )
            # If we receive an error in the callback GET parameters, this means that the
            # authentication could not be performed at the OP level. In that case we have to logout
            # the current user because we could've obtained this error after a prompt=none hit on
            # OpenID Connect Provider authenticate endpoint.
            logger.debug(log_prompt.format('Logout'))
            auth.logout(request)

        logger.debug(log_prompt.format('Redirect'))
        return HttpResponseRedirect(settings.AUTH_OPENID_AUTHENTICATION_FAILURE_REDIRECT_URI)


class OIDCEndSessionView(View):
    """ Allows to end the session of any user authenticated using OpenID Connect.

    This view acts as the main endpoint to end the session of an end-user that was authenticated
    using the OIDC provider (OP). It calls the "end-session" endpoint provided by the provider if
    applicable.

    """

    http_method_names = ['get', 'post', ]

    def get(self, request):
        """ Processes GET requests. """
        log_prompt = "Process GET requests [OIDCEndSessionView]: {}"
        logger.debug(log_prompt.format('Start'))
        return self.post(request)

    def post(self, request):
        """ Processes POST requests. """
        log_prompt = "Process POST requests [OIDCEndSessionView]: {}"
        logger.debug(log_prompt.format('Start'))

        logout_url = settings.LOGOUT_REDIRECT_URL or '/'

        # Log out the current user.
        if request.user.is_authenticated:
            logger.debug(log_prompt.format('Current user is authenticated'))
            try:
                logout_url = self.provider_end_session_url \
                    if settings.AUTH_OPENID_PROVIDER_END_SESSION_ENDPOINT else logout_url
            except KeyError:  # pragma: no cover
                logout_url = logout_url
            logger.debug(log_prompt.format('Log out the current user: {}'.format(request.user)))
            auth.logout(request)

        # Redirects the user to the appropriate URL.
        logger.debug(log_prompt.format('Redirect'))
        return HttpResponseRedirect(logout_url)

    @property
    def provider_end_session_url(self):
        """ Returns the end-session URL. """
        q = QueryDict(mutable=True)
        q[settings.AUTH_OPENID_PROVIDER_END_SESSION_REDIRECT_URI_PARAMETER] = \
            build_absolute_uri_for_oidc(self.request, path=settings.LOGOUT_REDIRECT_URL or '/')
        q[settings.AUTH_OPENID_PROVIDER_END_SESSION_ID_TOKEN_PARAMETER] = \
            self.request.session['oidc_auth_id_token']
        return '{}?{}'.format(settings.AUTH_OPENID_PROVIDER_END_SESSION_ENDPOINT, q.urlencode())
