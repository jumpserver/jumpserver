# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.contrib.auth import get_user_model

from common.permissions import ServiceAccountSignaturePermission
from .base import JMSBaseAuthBackend

UserModel = get_user_model()

__all__ = ['PublicKeyAuthBackend']


class PublicKeyAuthBackend(JMSBaseAuthBackend):
    @staticmethod
    def is_enabled():
        return settings.TERMINAL_PUBLIC_KEY_AUTH

    def authenticate(self, request, username=None, public_key=None, **kwargs):
        if not public_key:
            return None

        permission = ServiceAccountSignaturePermission()
        if not permission.has_permission(request, None):
            return None
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            return None
        else:
            if user.check_public_key(public_key) and \
                    self.user_can_authenticate(user):
                return user

    def get_user(self, user_id):
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
