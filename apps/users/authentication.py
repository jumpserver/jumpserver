# -*- coding: utf-8 -*-
#

import base64
import hashlib
import time

from django.core.cache import cache
from django.conf import settings
from django.utils.translation import ugettext as _
from rest_framework import authentication, exceptions, permissions
from django.utils.six import text_type
from django.utils.translation import ugettext_lazy as _
from rest_framework import HTTP_HEADER_ENCODING

from common.utils import get_object_or_none, make_signature, http_to_unixtime
from .utils import refresh_token
from .models import User, AccessKey, PrivateToken


def get_request_date_header(request):
    date = request.META.get('HTTP_DATE', b'')
    if isinstance(date, text_type):
        # Work around django test client oddness
        date = date.encode(HTTP_HEADER_ENCODING)
    return date


class AccessKeyAuthentication(authentication.BaseAuthentication):
    keyword = 'Sign'
    model = AccessKey

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid signature header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid signature header. Signature string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)


        try:
            sign = auth[1].decode().split(':')
            if len(sign) != 2:
                msg = _('Invalid signature header. Format like AccessKeyId:Signature')
                raise exceptions.AuthenticationFailed(msg)
        except UnicodeError:
            msg = _('Invalid signature header. Signature string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        access_key_id = sign[0]
        request_signature = sign[1]

        return self.authenticate_credentials(request, access_key_id, request_signature)

    def authenticate_credentials(self, request, access_key_id, request_signature):
        access_key = get_object_or_none(AccessKey, id=access_key_id)
        request_date = get_request_date_header(request)
        if access_key is None or not access_key.user:
            raise exceptions.AuthenticationFailed(_('Invalid signature.'))
        access_key_secret = access_key.secret

        print(request_date)

        try:
            request_unix_time = http_to_unixtime(request_date)
        except ValueError:
            raise exceptions.AuthenticationFailed(_('HTTP header: Date not provide or not %a, %d %b %Y %H:%M:%S GMT'))

        if int(time.time()) - request_unix_time > 15*60:
            raise exceptions.AuthenticationFailed(_('Expired, more than 15 minutes'))

        signature = make_signature(access_key_secret, request_date)
        if not signature == request_signature:
            raise exceptions.AuthenticationFailed(_('Invalid signature. %s: %s' % (signature, request_signature)))

        if not access_key.user.is_active:
            raise exceptions.AuthenticationFailed(_('User disabled.'))

        return access_key.user, None


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
        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token):
        user_id = cache.get(token)
        user = get_object_or_none(User, id=user_id)

        if not user:
            msg = _('Invalid token or cache refreshed.')
            raise exceptions.AuthenticationFailed(msg)
        refresh_token(token, user)
        return user, None


class PrivateTokenAuthentication(authentication.TokenAuthentication):
    model = PrivateToken
