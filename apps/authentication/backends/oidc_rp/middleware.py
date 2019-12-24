# -*- coding: utf-8 -*-
# @Time    : 2019/11/22 1:49 下午
# @Author  : Alex
# @Email   : 1374462869@qq.com
# @Project : jumpserver
# @File    : middleware.py
import time
from django.conf import settings

class OIDCRefreshIDTokenMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'GET' and not request.is_ajax() and request.user.is_authenticated:
            self.refresh_token(request)
        response = self.get_response(request)
        return response

    def refresh_token(self, request):
        refresh_token = request.session.get('oidc_auth_refresh_token')
        if refresh_token is None:
            return
        id_token_exp_timestamp = request.session.get('oidc_auth_id_token_exp_timestamp', None)
        now_timestamp = time.time()
        if id_token_exp_timestamp is not None and id_token_exp_timestamp > now_timestamp:
            return

        refresh_token = request.session.pop('oidc_auth_refresh_token')
        token_payload = {
            'client_id': settings.AUTH_OPENID_CLIENT_ID,
            'client_secret': settings.AUTH_OPENID_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        }




