# -*- coding: utf-8 -*-
#

from django.contrib.auth import get_user_model
from radiusauth.backends import RADIUSBackend

User = get_user_model()


class RadiusBackend(RADIUSBackend):
    def get_django_user(self, username, password=None):
        if isinstance(username, bytes):
            username = username.decode()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User(username=username, name=username)
            user.source = user.SOURCE_RADIUS
            user.save()
        return user
