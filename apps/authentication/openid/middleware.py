# coding:utf-8
#

from django.conf import settings
from django.utils.functional import SimpleLazyObject
from django.contrib.auth import authenticate
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import BACKEND_SESSION_KEY
from requests.exceptions import HTTPError
from django.contrib.auth import logout

from authentication.openid.services import client
from .models import OIDC_ACCESS_TOKEN


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

        # 不用 openid auth

        if not settings.AUTH_OPENID:
            return None

        # 启用 openid auth
        super(OpenIDAuthenticationMiddleware, self).process_request(request)

        # api

        # coco 用户 authenticate
        if False:
            user = authenticate(request=request, username='xiaobai', password='xiaobai')
            return
            # return HttpResponse(user)

        # core
        # 检验用户有效(使用access_token)
        # 用户还没有认证
        if not request.user.is_authenticated:
            return

        # 判断openid用户是否单点退出
        try:
            userinfo = request.client.openid_api_client.userinfo(
                token=request.session.get(OIDC_ACCESS_TOKEN))
        except HTTPError:
            logout(request)
