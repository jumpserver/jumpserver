# -*- coding: utf-8 -*-
#
import time
from rest_framework import permissions
from django.conf import settings
from common.exceptions import MFAVerifyRequired


class IsValidUser(permissions.IsAuthenticated, permissions.BasePermission):
    """Allows access to valid user, is active and not expired"""

    def has_permission(self, request, view):
        return super(IsValidUser, self).has_permission(request, view) \
               and request.user.is_valid


class OnlySuperUser(IsValidUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) \
               and request.user.is_superuser


class WithBootstrapToken(permissions.BasePermission):
    def has_permission(self, request, view):
        authorization = request.META.get('HTTP_AUTHORIZATION', '')
        if not authorization:
            return False
        request_bootstrap_token = authorization.split()[-1]
        return settings.BOOTSTRAP_TOKEN == request_bootstrap_token


class NeedMFAVerify(permissions.BasePermission):
    def has_permission(self, request, view):
        if not settings.SECURITY_VIEW_AUTH_NEED_MFA:
            return True

        mfa_verify_time = request.session.get('MFA_VERIFY_TIME', 0)
        if time.time() - mfa_verify_time < settings.SECURITY_MFA_VERIFY_TTL:
            return True
        raise MFAVerifyRequired()


class IsObjectOwner(IsValidUser):
    def has_object_permission(self, request, view, obj):
        return (super().has_object_permission(request, view, obj) and
                request.user == getattr(obj, 'user', None))
