# -*- coding: utf-8 -*-
#
import base64
import hashlib
import hmac
import os
from datetime import timezone as datetime_timezone
from email.utils import parsedate_to_datetime

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import authentication, exceptions

from accounts.models import IntegrationApplication
from common.auth import signature
from common.decorators import merge_delay_run
from common.utils import get_object_or_none, get_request_ip_or_data, contains_ip, get_request_ip
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


@merge_delay_run(ttl=60)
def update_service_integration_last_used(service_integrations=()):
    IntegrationApplication.objects.filter(
        id__in=service_integrations
    ).update(date_last_used=timezone.now())


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
        if not user:
            return None
        after_authenticate_update_date(user)
        return user, header

    @staticmethod
    def authenticate_credentials(token):
        model = get_user_model()
        user_id = cache.get(token)
        user = get_object_or_none(model, id=user_id)
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
        if not user or not user.is_active or not user.is_valid:
            return None

        ignore_csrf_check = os.environ.get("DOMAINS", "") == "*"
        if not ignore_csrf_check:
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
            if not key.is_valid:
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


class ServiceAuthentication(signature.SignatureAuthentication):
    __instance = None
    source = 'jms-pam'

    def get_object(self, key_id):
        if not self.__instance:
            self.__instance = IntegrationApplication.objects.filter(
                id=key_id, is_active=True,
            ).first()
        return self.__instance

    def fetch_user_data(self, key_id, algorithm=None):
        obj = self.get_object(key_id)
        if not obj:
            return None, None
        return obj, obj.secret

    def is_ip_allow(self, key_id, request):
        obj = self.get_object(key_id)
        if not contains_ip(get_request_ip(request), obj.ip_group):
            return False
        return True

    def after_authenticate_update_date(self, user):
        update_service_integration_last_used.delay((user.id,))


class CredentialServiceAuthentication(ServiceAuthentication):
    required_headers = [
        '(request-target)', 'date', 'x-jms-org', 'x-source', 'x-jms-nonce',
    ]
    max_clock_skew = 300

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request)
        try:
            method, fields = signature.utils.parse_authorization_header(
                auth_header,
            )
            if method.lower() != 'signature':
                return None
            if fields.get('algorithm', '').lower() != 'hmac-sha256':
                raise signature.FAILED
            signed_headers = set(
                fields.get('headers', '').lower().split()
            )
            if not set(self.required_headers).issubset(signed_headers):
                raise signature.FAILED
            if request.headers.get('Idempotency-Key') \
                    and 'idempotency-key' not in signed_headers:
                raise signature.FAILED
            nonce = request.headers.get('X-JMS-Nonce', '')
            if not 16 <= len(nonce) <= 128:
                raise signature.FAILED

            body = request.body or b''
            if body:
                if 'digest' not in signed_headers:
                    raise signature.FAILED
                digest = 'SHA-256=' + base64.b64encode(
                    hashlib.sha256(body).digest()
                ).decode()
                if not hmac.compare_digest(
                    request.headers.get('Digest', ''), digest,
                ):
                    raise signature.FAILED

            request_date = parsedate_to_datetime(request.headers.get('Date', ''))
            if request_date.tzinfo is None:
                request_date = request_date.replace(
                    tzinfo=datetime_timezone.utc,
                )
            if abs((timezone.now() - request_date).total_seconds()) \
                    > self.max_clock_skew:
                raise signature.FAILED
        except exceptions.AuthenticationFailed:
            raise
        except Exception:
            raise signature.FAILED

        try:
            result = super().authenticate(request)
        except DjangoValidationError:
            raise signature.FAILED
        if not result:
            return result
        user, __ = result
        if str(request.headers.get('X-JMS-ORG')) != str(user.org_id):
            raise signature.FAILED
        replay_key = 'credential-signature:' + hashlib.sha256(
            f'{fields["keyid"]}:{nonce}'.encode(),
        ).hexdigest()
        if not cache.add(
            replay_key, True, timeout=self.max_clock_skew * 2,
        ):
            raise signature.FAILED
        return result
