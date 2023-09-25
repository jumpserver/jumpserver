# -*- coding: utf-8 -*-
#
import time

from django.conf import settings
from rest_framework import permissions

from authentication.const import ConfirmType
from authentication.models import ConnectionToken
from common.exceptions import UserConfirmRequired
from common.utils import get_object_or_none
from orgs.utils import tmp_to_root_org


class IsValidUser(permissions.IsAuthenticated):
    """Allows access to valid user, is active and not expired"""

    def has_permission(self, request, view):
        return super().has_permission(request, view) \
            and request.user.is_valid


class IsValidUserOrConnectionToken(IsValidUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) \
            or self.is_valid_connection_token(request)

    @staticmethod
    def is_valid_connection_token(request):
        token_id = request.query_params.get('token')
        if not token_id:
            return False
        with tmp_to_root_org():
            token = get_object_or_none(ConnectionToken, id=token_id)
        return token and token.is_valid


class OnlySuperUser(IsValidUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) \
            and request.user.is_superuser


class IsServiceAccount(IsValidUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) \
            and request.user.is_service_account


class WithBootstrapToken(permissions.BasePermission):
    def has_permission(self, request, view):
        authorization = request.META.get('HTTP_AUTHORIZATION', '')
        if not authorization:
            return False
        request_bootstrap_token = authorization.split()[-1]
        return settings.BOOTSTRAP_TOKEN == request_bootstrap_token


class UserConfirmation(permissions.BasePermission):
    ttl = 60 * 5
    min_level = 1
    confirm_type = ConfirmType.ReLogin

    def has_permission(self, request, view):
        if not settings.SECURITY_VIEW_AUTH_NEED_MFA:
            return True

        confirm_level = request.session.get('CONFIRM_LEVEL')
        confirm_time = request.session.get('CONFIRM_TIME')
        ttl = self.get_ttl()
        if not confirm_level or not confirm_time or \
                confirm_level < self.min_level or \
                confirm_time < time.time() - ttl:
            raise UserConfirmRequired(code=self.confirm_type)
        return True

    def get_ttl(self):
        if self.confirm_type == ConfirmType.MFA:
            ttl = settings.SECURITY_MFA_VERIFY_TTL
        else:
            ttl = self.ttl
        return ttl

    @classmethod
    def require(cls, confirm_type=ConfirmType.ReLogin, ttl=60 * 5):
        min_level = ConfirmType.values.index(confirm_type) + 1
        name = 'UserConfirmationLevel{}TTL{}'.format(min_level, ttl)
        return type(name, (cls,), {'min_level': min_level, 'ttl': ttl, 'confirm_type': confirm_type})


class ServiceAccountSignaturePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        from authentication.models import AccessKey
        from common.utils.crypto import get_aes_crypto
        signature = request.META.get('HTTP_X_JMS_SVC', '')
        if not signature or not signature.startswith('Sign'):
            return False
        data = signature[4:].strip()
        if not data or ':' not in data:
            return False
        ak_id, time_sign = data.split(':', 1)
        if not ak_id or not time_sign:
            return False
        ak = AccessKey.objects.filter(id=ak_id).first()
        if not ak or not ak.is_active:
            return False
        if not ak.user or not ak.user.is_active or not ak.user.is_service_account:
            return False
        aes = get_aes_crypto(str(ak.secret).replace('-', ''), mode='ECB')
        try:
            timestamp = aes.decrypt(time_sign)
            if not timestamp or not timestamp.isdigit():
                return False
            timestamp = int(timestamp)
            interval = abs(int(time.time()) - timestamp)
            if interval > 30:
                return False
            return True
        except Exception:
            return False

    def has_object_permission(self, request, view, obj):
        return False
