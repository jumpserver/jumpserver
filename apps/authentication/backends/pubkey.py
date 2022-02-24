# -*- coding: utf-8 -*-
#
from django.contrib.auth import get_user_model
from django.conf import settings

from .base import JMSBaseAuthBackend

UserModel = get_user_model()

__all__ = ['PublicKeyAuthBackend']


class PublicKeyAuthBackend(JMSBaseAuthBackend):
    @classmethod
    def is_enabled(cls):
        return settings.TERMINAL_PUBLIC_KEY_AUTH

    def authenticate(self, request, username=None, public_key=None, **kwargs):
        if not public_key:
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

    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        that attribute are allowed.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None

    def get_user(self, user_id):
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
