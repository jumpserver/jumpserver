# -*- coding: utf-8 -*-
#

import base64

from django.core.cache import cache
from django.conf import settings
from django.utils.translation import ugettext as _
from rest_framework import authentication, exceptions, permissions
from rest_framework.compat import is_authenticated

from common.utils import signer, get_object_or_none
from .hands import Terminal
from .utils import get_or_refresh_token
from .models import User


class TerminalAuthentication(authentication.BaseAuthentication):
    keyword = 'Sign'
    model = Terminal

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid sign header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid sign header. Sign string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            sign = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Sign string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)
        return self.authenticate_credentials(sign)

    def authenticate_credentials(self, sign):
        name = signer.unsign(sign)
        if name:
            terminal = get_object_or_none(self.model, name=name)
        else:
            raise exceptions.AuthenticationFailed(_('Invalid sign.'))

        if not terminal or not terminal.is_active:
            raise exceptions.AuthenticationFailed(_('Terminal inactive or deleted.'))
        terminal.is_authenticated = True
        return terminal, None


class AccessTokenAuthentication(authentication.BaseAuthentication):
    keyword = 'Bearer'
    model = User
    expiration = settings.CONFIG.TOKEN_EXPIRATION or 3600

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Sign string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Sign string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)
        return self.authenticate_credentials(token, request)

    def authenticate_credentials(self, token, request):
        user_id = cache.get(token)
        print('Auth id: %s' % user_id)
        user = get_object_or_none(User, id=user_id)

        if not user:
            return None
        get_or_refresh_token(request, user)
        return user, None
