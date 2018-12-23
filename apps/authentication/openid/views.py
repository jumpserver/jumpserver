# -*- coding: utf-8 -*-
#

import logging

from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from django.views.generic.base import RedirectView
from django.contrib.auth import authenticate, login
from django.http.response import (
    HttpResponseBadRequest,
    HttpResponseServerError,
    HttpResponseRedirect
)

from . import client
from .models import Nonce
from users.models import LoginLog
from users.tasks import write_login_log_async
from common.utils import get_request_ip

logger = logging.getLogger(__name__)


def get_base_site_url():
    return settings.BASE_SITE_URL


class LoginView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        nonce = Nonce(
            redirect_uri=get_base_site_url() + reverse(
                "authentication:openid-login-complete"),

            next_path=self.request.GET.get('next')
        )

        cache.set(str(nonce.state), nonce, 24*3600)

        self.request.session['openid_state'] = str(nonce.state)

        authorization_url = client.openid_connect_client.\
            authorization_url(
                redirect_uri=nonce.redirect_uri, scope='code',
                state=str(nonce.state)
            )

        return authorization_url


class LoginCompleteView(RedirectView):

    def get(self, request, *args, **kwargs):
        if 'error' in request.GET:
            return HttpResponseServerError(self.request.GET['error'])

        if 'code' not in self.request.GET and 'state' not in self.request.GET:
            return HttpResponseBadRequest()

        if self.request.GET['state'] != self.request.session['openid_state']:
            return HttpResponseBadRequest()

        nonce = cache.get(self.request.GET['state'])

        if not nonce:
            return HttpResponseBadRequest()

        user = authenticate(
            request=self.request,
            code=self.request.GET['code'],
            redirect_uri=nonce.redirect_uri
        )

        cache.delete(str(nonce.state))

        if not user:
            return HttpResponseBadRequest()

        login(self.request, user)

        data = {
            'username': user.username,
            'mfa': int(user.otp_enabled),
            'reason': LoginLog.REASON_NOTHING,
            'status': True
        }
        self.write_login_log(data)

        return HttpResponseRedirect(nonce.next_path or '/')

    def write_login_log(self, data):
        login_ip = get_request_ip(self.request)
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        tmp_data = {
            'ip': login_ip,
            'type': 'W',
            'user_agent': user_agent
        }
        data.update(tmp_data)
        write_login_log_async.delay(**data)
