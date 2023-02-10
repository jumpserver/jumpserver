from django.views import View
from django.conf import settings
from django.contrib import auth
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.http import urlencode

from authentication.utils import build_absolute_uri
from common.utils import get_logger
from authentication.mixins import authenticate

logger = get_logger(__file__)


class OAuth2AuthRequestView(View):

    def get(self, request):
        log_prompt = "Process OAuth2 GET requests: {}"
        logger.debug(log_prompt.format('Start'))

        query_dict = {
            'client_id': settings.AUTH_OAUTH2_CLIENT_ID, 'response_type': 'code',
            'scope': settings.AUTH_OAUTH2_SCOPE,
            'redirect_uri': build_absolute_uri(
                request, path=reverse(settings.AUTH_OAUTH2_AUTH_LOGIN_CALLBACK_URL_NAME)
            )
        }

        if '?' in settings.AUTH_OAUTH2_PROVIDER_AUTHORIZATION_ENDPOINT:
            separator = '&'
        else:
            separator = '?'
        redirect_url = '{url}{separator}{query}'.format(
            url=settings.AUTH_OAUTH2_PROVIDER_AUTHORIZATION_ENDPOINT,
            separator=separator,
            query=urlencode(query_dict)
        )
        logger.debug(log_prompt.format('Redirect login url'))
        return HttpResponseRedirect(redirect_url)


class OAuth2AuthCallbackView(View):
    http_method_names = ['get', ]

    def get(self, request):
        """ Processes GET requests. """
        log_prompt = "Process GET requests [OAuth2AuthCallbackView]: {}"
        logger.debug(log_prompt.format('Start'))
        callback_params = request.GET

        if 'code' in callback_params:
            logger.debug(log_prompt.format('Process authenticate'))
            user = authenticate(code=callback_params['code'], request=request)
            if user and user.is_valid:
                logger.debug(log_prompt.format('Login: {}'.format(user)))
                auth.login(self.request, user)
                logger.debug(log_prompt.format('Redirect'))
                return HttpResponseRedirect(
                    settings.AUTH_OAUTH2_AUTHENTICATION_REDIRECT_URI
                )

        logger.debug(log_prompt.format('Redirect'))
        # OAuth2 服务端认证成功, 但是用户被禁用了, 这时候需要调用服务端的logout
        redirect_url = settings.AUTH_OAUTH2_PROVIDER_END_SESSION_ENDPOINT
        return HttpResponseRedirect(redirect_url)


class OAuth2EndSessionView(View):
    http_method_names = ['get', 'post', ]

    def get(self, request):
        """ Processes GET requests. """
        log_prompt = "Process GET requests [OAuth2EndSessionView]: {}"
        logger.debug(log_prompt.format('Start'))
        return self.post(request)

    def post(self, request):
        """ Processes POST requests. """
        log_prompt = "Process POST requests [OAuth2EndSessionView]: {}"
        logger.debug(log_prompt.format('Start'))

        logout_url = settings.LOGOUT_REDIRECT_URL or '/'

        # Log out the current user.
        if request.user.is_authenticated:
            logger.debug(log_prompt.format('Log out the current user: {}'.format(request.user)))
            auth.logout(request)

            logout_url = settings.AUTH_OAUTH2_PROVIDER_END_SESSION_ENDPOINT
            if settings.AUTH_OAUTH2_LOGOUT_COMPLETELY and logout_url:
                logger.debug(log_prompt.format('Log out OAUTH2 platform user session synchronously'))
                return HttpResponseRedirect(logout_url)

        logger.debug(log_prompt.format('Redirect'))
        return HttpResponseRedirect(logout_url)
