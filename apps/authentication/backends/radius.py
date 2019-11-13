# -*- coding: utf-8 -*-
#

from django.contrib.auth import get_user_model
from radiusauth.backends import RADIUSBackend, RADIUSRealmBackend
from django.conf import settings

from pyrad.packet import AccessRequest

User = get_user_model()


class CreateUserMixin:
    def get_django_user(self, username, password=None):
        if isinstance(username, bytes):
            username = username.decode()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if '@' in username:
                email = username
            else:
                email_suffix = settings.EMAIL_SUFFIX
                email = '{}@{}'.format(username, email_suffix)
            user = User(username=username, name=username, email=email)
            user.source = user.SOURCE_RADIUS
            user.save()
        return user

    def _get_auth_packet(self, username, password, client):
        """
        Get the pyrad authentication packet for the username/password and the
        given pyrad client.
        """
        pkt = client.CreateAuthPacket(code=AccessRequest,
                                      User_Name=username)
        if settings.CONFIG.RADIUS_ENCRYPT_PASSWORD:
            password = pkt.PwCrypt(password)
        else:
            password = password
        pkt["User-Password"] = password
        pkt["NAS-Identifier"] = 'django-radius'
        for key, val in list(getattr(settings, 'RADIUS_ATTRIBUTES', {}).items()):
            pkt[key] = val
        return pkt


class RadiusBackend(CreateUserMixin, RADIUSBackend):
    pass


class RadiusRealmBackend(CreateUserMixin, RADIUSRealmBackend):
    pass


class TestRadiusPyRadius(object):

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.secret = settings.CONFIG.RADIUS_SECRET
        self.host = settings.CONFIG.RADIUS_SERVER
        self.port = settings.CONFIG.RADIUS_PORT

    def attr_to_json(self):
        attr_json = {
            'username': self.username,
            'password': self.password,
            'secret': self.secret,
            'host': self.host,
            'port': self.port
        }
        return attr_json

    def authenticate(self):
        import radius
        print('Authenticate Radius start: ')
        params = self.attr_to_json()
        print("Params: {}".format(params))
        r = radius.authenticate(
            self.username, self.password,
            self.secret, host=self.host, port=int(self.port)
        )
        print("Result: {}".format(r))
