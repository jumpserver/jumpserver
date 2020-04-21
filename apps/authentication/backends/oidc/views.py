from django.conf import settings
from django.http import HttpResponseRedirect, QueryDict
from oidc_rp.conf import settings as oidc_rp_settings
from oidc_rp.views import OIDCEndSessionView

__all__ = ['OverwriteOIDCEndSessionView']


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

