# -*- coding: utf-8 -*-
#
import traceback

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from radiusauth.backends import RADIUSBackend, RADIUSRealmBackend

from authentication.backends.base import JMSBaseAuthBackend
from common.utils import get_logger
from users.validators import get_validation_error_message
from .signals import radius_create_user

User = get_user_model()
logger = get_logger(__file__)


class CreateUserMixin:
    @staticmethod
    def get_django_user(username, password=None, *args, **kwargs):
        if isinstance(username, bytes):
            username = username.decode()
        user = User.objects.filter(username=username).first()
        if user:
            return user

        if '@' in username:
            email = username
        else:
            email_suffix = settings.EMAIL_SUFFIX
            email = '{}@{}'.format(username, email_suffix)

        user = User(username=username, name=username, email=email)
        try:
            user.save()
        except ValidationError as e:
            logger.warning(
                'Create RADIUS user failed: {}'.format(get_validation_error_message(e))
            )
            return None
        radius_create_user.send(sender=user.__class__, user=user)
        return user

    def _perform_radius_auth(self, client, packet):
        # TODO: 等待官方库修复这个BUG
        try:
            return super()._perform_radius_auth(client, packet)
        except UnicodeError as e:
            import sys
            tb = ''.join(traceback.format_exception(*sys.exc_info(), limit=2, chain=False))
            if tb.find("cl.decode") != -1:
                return [], False, False
            return None


class RadiusBaseBackend(CreateUserMixin, JMSBaseAuthBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_RADIUS


class RadiusBackend(RadiusBaseBackend, RADIUSBackend):
    def authenticate(self, request, username='', password=''):
        return super().authenticate(request, username=username, password=password)


class RadiusRealmBackend(RadiusBaseBackend, RADIUSRealmBackend):
    def authenticate(self, request, username='', password='', realm=None):
        return super().authenticate(request, username=username, password=password, realm=realm)
