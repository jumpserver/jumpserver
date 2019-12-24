# -*- coding: utf-8 -*-
# @Time    : 2019/11/22 1:50 下午
# @Author  : Alex
# @Email   : 1374462869@qq.com
# @Project : jumpserver
# @File    : views.py

from django.views.generic import View
from django.conf import settings
# from django.utils.crypto import get_random_string
from django.utils.http import is_safe_url, urlencode
from django.http import HttpResponseRedirect, QueryDict
from django.contrib import auth
from .signals import post_openid_login_success

class OIDCAuthRequestView(View):

    http_method_names = ['get',]

    def get(self, request):
        redirect_uri = settings.BASE_SITE_URL + str(settings.LOGIN_COMPLETE_URL)
        authentication_request_params = request.GET.dict()
        authentication_request_params.update({
            'response_type': 'code',
            'client_id': settings.AUTH_OPENID_CLIENT_ID,
            'redirect_uri': redirect_uri,
        })

        next_url = request.GET.get('next')
        request.session['oidc_auth_next_url'] = next_url \
            if is_safe_url(url=next_url, allowed_hosts=(request.get_host(), )) else None

        query = urlencode(authentication_request_params)
        redirect_url = '{url}?{query}'.format(
            url=settings.AUTH_OPENID_SERVER_URL, query=query)
        return HttpResponseRedirect(redirect_url)


class OIDCAuthCallbackView(View):

    http_method_names = ['get', ]

    def get(self, request):
        callback_params = request.GET
        if 'code' in callback_params:
            next_url = request.session.get('oidc_auth_next_url', None)
            user = auth.authenticate(request=request)
            if user and user.is_active:
                auth.login(self.request, user)
                post_openid_login_success.send(
                    sender=self.__class__, user=user, request=self.request
                )
                return HttpResponseRedirect(
                    next_url or '/')

        if 'error' in callback_params:
                auth.logout(request)

        return HttpResponseRedirect('/')
