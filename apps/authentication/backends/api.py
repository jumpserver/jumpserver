# -*- coding: utf-8 -*-
#

import uuid
import time

from django.core.cache import cache
from django.utils.translation import ugettext as _
from six import text_type
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework import authentication, exceptions
from common.auth import signature

from common.utils import get_object_or_none, make_signature, http_to_unixtime
from ..models import AccessKey, PrivateToken


def get_request_date_header(request):
    date = request.META.get('HTTP_DATE', b'')
    if isinstance(date, text_type):
        # Work around django test client oddness
        date = date.encode(HTTP_HEADER_ENCODING)
    return date


class AccessKeyAuthentication(authentication.BaseAuthentication):
    """App使用Access key进行签名认证, 目前签名算法比较简单,
    app注册或者手动建立后,会生成 access_key_id 和 access_key_secret,
    然后使用 如下算法生成签名:
    Signature = md5(access_key_secret + '\n' + Date)
    example: Signature = md5('d32d2b8b-9a10-4b8d-85bb-1a66976f6fdc' + '\n' +
                    'Thu, 12 Jan 2017 08:19:41 GMT')
    请求时设置请求header
    header['Authorization'] = 'Sign access_key_id:Signature' 如:
    header['Authorization'] =
        'Sign d32d2b8b-9a10-4b8d-85bb-1a66976f6fdc:OKOlmdxgYPZ9+SddnUUDbQ=='

    验证时根据相同算法进行验证, 取到access_key_id对应的access_key_id, 从request
    headers取到Date, 然后进行md5, 判断得到的结果是否相同, 如果是认证通过, 否则 认证
    失败
    """
    keyword = 'Sign'

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid signature header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid signature header. Signature '
                    'string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            sign = auth[1].decode().split(':')
            if len(sign) != 2:
                msg = _('Invalid signature header. '
                        'Format like AccessKeyId:Signature')
                raise exceptions.AuthenticationFailed(msg)
        except UnicodeError:
            msg = _('Invalid signature header. '
                    'Signature string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        access_key_id = sign[0]
        try:
            uuid.UUID(access_key_id)
        except ValueError:
            raise exceptions.AuthenticationFailed('Access key id invalid')
        request_signature = sign[1]

        return self.authenticate_credentials(
            request, access_key_id, request_signature
        )

    @staticmethod
    def authenticate_credentials(request, access_key_id, request_signature):
        access_key = get_object_or_none(AccessKey, id=access_key_id)
        request_date = get_request_date_header(request)
        if access_key is None or not access_key.user:
            raise exceptions.AuthenticationFailed(_('Invalid signature.'))
        access_key_secret = access_key.secret

        try:
            request_unix_time = http_to_unixtime(request_date)
        except ValueError:
            raise exceptions.AuthenticationFailed(
                _('HTTP header: Date not provide '
                  'or not %a, %d %b %Y %H:%M:%S GMT'))

        if int(time.time()) - request_unix_time > 15 * 60:
            raise exceptions.AuthenticationFailed(
                _('Expired, more than 15 minutes'))

        signature = make_signature(access_key_secret, request_date)
        if not signature == request_signature:
            raise exceptions.AuthenticationFailed(_('Invalid signature.'))

        if not access_key.user.is_active:
            raise exceptions.AuthenticationFailed(_('User disabled.'))
        return access_key.user, None

    def authenticate_header(self, request):
        return 'Sign access_key_id:Signature'


class AccessTokenAuthentication(authentication.BaseAuthentication):
    keyword = 'Bearer'
    # expiration = settings.TOKEN_EXPIRATION or 3600
    model = get_user_model()

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Sign string '
                    'should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Sign string '
                    'should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)
        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token):
        model = get_user_model()
        user_id = cache.get(token)
        user = get_object_or_none(model, id=user_id)

        if not user:
            msg = _('Invalid token or cache refreshed.')
            raise exceptions.AuthenticationFailed(msg)
        return user, None

    def authenticate_header(self, request):
        return self.keyword


class PrivateTokenAuthentication(authentication.TokenAuthentication):
    model = PrivateToken


class SessionAuthentication(authentication.SessionAuthentication):
    def authenticate(self, request):
        """
        Returns a `User` if the request session currently has a logged in user.
        Otherwise returns `None`.
        """

        # Get the session-based user from the underlying HttpRequest object
        user = getattr(request._request, 'user', None)

        # Unauthenticated, CSRF validation not required
        if not user or not user.is_active:
            return None

        try:
            self.enforce_csrf(request)
        except exceptions.AuthenticationFailed:
            return None

        # CSRF passed with authenticated user
        return user, None


class SignatureAuthentication(signature.SignatureAuthentication):
    # The HTTP header used to pass the consumer key ID.

    # A method to fetch (User instance, user_secret_string) from the
    # consumer key ID, or None in case it is not found. Algorithm
    # will be what the client has sent, in the case that both RSA
    # and HMAC are supported at your site (and also for expansion).
    model = get_user_model()

    def fetch_user_data(self, key_id, algorithm="hmac-sha256"):
        # ...
        # example implementation:
        try:
            key = AccessKey.objects.get(id=key_id)
            if not key.is_active:
                return None, None
            user, secret = key.user, str(key.secret)
            return user, secret
        except AccessKey.DoesNotExist:
            return None, None


class SSOAuthentication(ModelBackend):
    """
    什么也不做呀😺
    """

    def authenticate(self, request, sso_token=None, **kwargs):
        pass
