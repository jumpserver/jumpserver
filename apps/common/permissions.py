# -*- coding: utf-8 -*-
#
import time

from django.conf import settings
from rest_framework import permissions
from rest_framework.request import Request

from authentication.const import ConfirmType
from common.exceptions import UserConfirmRequired


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


class UserConfirm(permissions.BasePermission):
    confirm_type: str

    def has_permission(self, request, view):
        if not settings.SECURITY_VIEW_AUTH_NEED_MFA:
            return True

        if self.validate(request):
            return True

        raise UserConfirmRequired(code=self.confirm_type)

    def is_allow(self, request: Request, confirm_type: str = None) -> bool:
        confirm_time = self.confirm_time(request, confirm_type)
        if time.time() - confirm_time < settings.SECURITY_MFA_VERIFY_TTL:
            return True
        return False

    def validate(self, request: Request):
        session_confirm_type = request.session.get('CONFIRM_TYPE')
        if not session_confirm_type or session_confirm_type == self.confirm_type:
            self.set_session(request)
            return self.is_allow(request)

        is_high_priority = ConfirmType.compare(self.confirm_type, session_confirm_type)
        current_result = self.is_allow(request)
        session_result = self.is_allow(request, session_confirm_type)

        if is_high_priority:
            self.set_session(request)
            return current_result

        if session_result:
            return True

        self.set_session(request)
        return current_result

    def confirm_time(self, request: Request, confirm_type: str = None):
        confirm_type = confirm_type or self.confirm_type
        session_key = f'{confirm_type.upper()}_USER_CONFIRM_TIME'
        return request.session.get(session_key, 0)

    def set_session(self, request: Request):
        request.session['CONFIRM_TYPE'] = self.confirm_type


class MFAUserConfirm(UserConfirm):
    confirm_type = ConfirmType.MFA


class PasswordUserConfirm(UserConfirm):
    confirm_type = ConfirmType.PASSWORD


class ReLoginUserConfirm(UserConfirm):
    confirm_type = ConfirmType.ReLogin


class IsObjectOwner(IsValidUser):
    def has_object_permission(self, request, view, obj):
        return (super().has_object_permission(request, view, obj) and
                request.user == getattr(obj, 'user', None))
