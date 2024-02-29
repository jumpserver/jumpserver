# -*- coding: utf-8 -*-
#

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import authentication, exceptions

from common.auth import signature
from common.decorators import merge_delay_run
from common.utils import get_object_or_none, get_request_ip_or_data, contains_ip
from users.models import User
from ..models import AccessKey, PrivateToken


def date_more_than(d, seconds):
    return d is None or (timezone.now() - d).seconds > seconds


@merge_delay_run(ttl=60)
def update_token_last_used(tokens=()):
    access_keys_ids = [token.id for token in tokens if isinstance(token, AccessKey)]
    private_token_keys = [token.key for token in tokens if isinstance(token, PrivateToken)]
    if len(access_keys_ids) > 0:
        AccessKey.objects.filter(id__in=access_keys_ids).update(date_last_used=timezone.now())
    if len(private_token_keys) > 0:
        PrivateToken.objects.filter(key__in=private_token_keys).update(date_last_used=timezone.now())


@merge_delay_run(ttl=60)
def update_user_last_used(users=()):
    User.objects.filter(id__in=users).update(date_api_key_last_used=timezone.now())


def after_authenticate_update_date(user, token=None):
    update_user_last_used.delay(users=(user.id,))
    if token:
        update_token_last_used.delay(tokens=(token,))


class AccessTokenAuthentication(authentication.BaseAuthentication):
    keyword = 'Bearer'
    model = get_user_model()

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
        user, header = self.authenticate_credentials(token)
        after_authenticate_update_date(user)
        return user, header

    @staticmethod
    def authenticate_credentials(token):
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

    def authenticate(self, request):
        user_token = super().authenticate(request)
        if not user_token:
            return
        user, token = user_token
        after_authenticate_update_date(user, token)
        return user, token


class SessionAuthentication(authentication.SessionAuthentication):
    def authenticate(self, request):
        """
        Returns a `User` if the request session currently has a logged in user.
        Otherwise, returns `None`.
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
            after_authenticate_update_date(user, key)
            return user, secret
        except (AccessKey.DoesNotExist, exceptions.ValidationError):
            return None, None

    def is_ip_allow(self, key_id, request):
        try:
            ak = AccessKey.objects.get(id=key_id)
            ip_group = ak.ip_group
            ip = get_request_ip_or_data(request)
            if not contains_ip(ip, ip_group):
                return False
            return True
        except (AccessKey.DoesNotExist, exceptions.ValidationError):
            return False
