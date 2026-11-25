# -*- coding: utf-8 -*-
#
import traceback

from django.conf import settings
from django.contrib.auth import get_user_model
from pyrad.client import Timeout
from pyrad.packet import AccessAccept, AccessReject
from radiusauth.backends import RADIUSBackend, RADIUSRealmBackend

from authentication.backends.base import JMSBaseAuthBackend
from .signals import radius_create_user

User = get_user_model()


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
        user.save()
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

    def authenticate_push(self, username, timeout):
        client = self._get_client(self._get_server_from_settings())
        client.retries = 1
        client.timeout = timeout
        # A NUL yields one protected PAP block and decodes to an empty password.
        packet = self._get_auth_packet(username, '\0', client)
        packet['User-Name'] = username
        packet['User-Password'] = packet.PwCrypt('\0')
        try:
            reply = client.SendPacket(packet)
        except Timeout:
            return 'timed_out'
        return {AccessAccept: 'approved', AccessReject: 'rejected'}.get(reply.code, 'failed')


class RadiusRealmBackend(RadiusBaseBackend, RADIUSRealmBackend):
    def authenticate(self, request, username='', password='', realm=None):
        return super().authenticate(request, username=username, password=password, realm=realm)
