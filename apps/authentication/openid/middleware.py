# coding:utf-8
#

from django.conf import settings
from django.contrib.auth import logout
from django.utils.functional import SimpleLazyObject
from django.utils.deprecation import MiddlewareMixin
from requests.exceptions import HTTPError

from authentication.openid.services import client
from authentication.openid.models import OIDC_ACCESS_TOKEN


def get_client(request):
    if not hasattr(request, '_cache_client'):
        request._cache_client = client.new_client()
    return request._cache_client


class BaseOpenIDMiddleware(MiddlewareMixin):

    def process_request(self, request):
        """
        Adds Client to request.
        :param request: django request
        """
        request.client = SimpleLazyObject(lambda: get_client(request))


class OpenIDAuthenticationMiddleware(BaseOpenIDMiddleware):

    header_key = "HTTP_AUTHORIZATION"

    def process_request(self, request):

        # Don't need openid auth
        if not settings.AUTH_OPENID:
            return

        # coco app Don't need openid auth
        if self.header_key in request.META:
            print('[INFO] Coco App')
            return

        # auth openid
        super(OpenIDAuthenticationMiddleware, self).process_request(request)

        # user not authenticated don't need check single logout
        if not request.user.is_authenticated:
            return

        # Check openid user single logout or not with access_token
        try:
            request.client.openid_connect_api_client.userinfo(
                token=request.session.get(OIDC_ACCESS_TOKEN))
        except HTTPError:
            logout(request)
