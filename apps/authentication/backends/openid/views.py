# -*- coding: utf-8 -*-
#

import logging

from django.conf import settings
from django.core.cache import cache
from django.views.generic.base import RedirectView
from django.contrib.auth import authenticate, login
from django.http.response import (
    HttpResponseBadRequest,
    HttpResponseServerError,
    HttpResponseRedirect
)

from .utils import new_client
from .models import Nonce
from .signals import post_openid_login_success

logger = logging.getLogger(__name__)
client = new_client()

__all__ = ['OpenIDLoginView', 'OpenIDLoginCompleteView']


class OpenIDLoginView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        redirect_uri = settings.BASE_SITE_URL + str(settings.LOGIN_COMPLETE_URL)
        nonce = Nonce(
            redirect_uri=redirect_uri,
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


class OpenIDLoginCompleteView(RedirectView):

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
        post_openid_login_success.send(
            sender=self.__class__, user=user, request=self.request
        )
        return HttpResponseRedirect(nonce.next_path or '/')

