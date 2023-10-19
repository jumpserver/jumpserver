# -*- coding: utf-8 -*-
#
import time

from django.conf import settings
from rest_framework import permissions


class IsValidUser(permissions.IsAuthenticated):
    """Allows access to valid user, is active and not expired"""

    def has_permission(self, request, view):
        return super().has_permission(request, view) \
            and request.user.is_valid


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
