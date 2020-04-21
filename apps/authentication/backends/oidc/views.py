from django.conf import settings
from django.http import HttpResponseRedirect, QueryDict
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.http import is_safe_url, urlencode

from oidc_rp.conf import settings as oidc_rp_settings
from oidc_rp.views import OIDCEndSessionView, OIDCAuthRequestView

__all__ = ['OverwriteOIDCAuthRequestView', 'OverwriteOIDCEndSessionView']


class OverwriteOIDCAuthRequestView(OIDCAuthRequestView):
    def get(self, request):
        """ Processes GET requests. """
        # Defines common parameters used to bootstrap the authentication request.
        authentication_request_params = request.GET.dict()
        authentication_request_params.update({
            'scope': oidc_rp_settings.SCOPES,
            'response_type': 'code',
            'client_id': oidc_rp_settings.CLIENT_ID,
            'redirect_uri': request.build_absolute_uri(
                reverse(settings.OIDC_RP_LOGIN_CALLBACK_URL_NAME)
            ),
        })

        # States should be used! They are recommended in order to maintain state between the
        # authentication request and the callback.
        if oidc_rp_settings.USE_STATE:
            state = get_random_string(oidc_rp_settings.STATE_LENGTH)
            authentication_request_params.update({'state': state})
            request.session['oidc_auth_state'] = state

        # Nonces should be used too! In that case the generated nonce is stored both in the
        # authentication request parameters and in the user's session.
        if oidc_rp_settings.USE_NONCE:
            nonce = get_random_string(oidc_rp_settings.NONCE_LENGTH)
            authentication_request_params.update({'nonce': nonce, })
            request.session['oidc_auth_nonce'] = nonce

        # Stores the "next" URL in the session if applicable.
        next_url = request.GET.get('next')
        request.session['oidc_auth_next_url'] = next_url \
            if is_safe_url(url=next_url, allowed_hosts=(request.get_host(), )) else None

        # Redirects the user to authorization endpoint.
        query = urlencode(authentication_request_params)
        redirect_url = '{url}?{query}'.format(
            url=oidc_rp_settings.PROVIDER_AUTHORIZATION_ENDPOINT, query=query)
        return HttpResponseRedirect(redirect_url)


class OverwriteOIDCEndSessionView(OIDCEndSessionView):
    def post(self, request):
        """ Processes POST requests. """
        logout_url = settings.LOGOUT_REDIRECT_URL or '/'

        try:
            logout_url = self.provider_end_session_url \
                if oidc_rp_settings.PROVIDER_END_SESSION_ENDPOINT else logout_url
        except KeyError:  # pragma: no cover
            logout_url = logout_url

        # Redirects the user to the appropriate URL.
        return HttpResponseRedirect(logout_url)

    @property
    def provider_end_session_url(self):
        """ Returns the end-session URL. """
        q = QueryDict(mutable=True)
        q[oidc_rp_settings.PROVIDER_END_SESSION_REDIRECT_URI_PARAMETER] = \
            self.request.build_absolute_uri(settings.LOGOUT_REDIRECT_URL or '/')
        if self.request.session.get('oidc_auth_id_token'):
            q[oidc_rp_settings.PROVIDER_END_SESSION_ID_TOKEN_PARAMETER] = \
                self.request.session['oidc_auth_id_token']
        return '{}?{}'.format(oidc_rp_settings.PROVIDER_END_SESSION_ENDPOINT, q.urlencode())

