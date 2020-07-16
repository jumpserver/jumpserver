# -*- coding: utf-8 -*-
#

from django.contrib.auth import get_user_model
from radiusauth.backends import RADIUSBackend, RADIUSRealmBackend
from django.conf import settings

from pyrad.packet import AccessRequest

User = get_user_model()


class CreateUserMixin:
    def get_django_user(self, username, password=None, *args, **kwargs):
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

    def authenticate(self, *args, **kwargs):
        # 校验用户时，会传入public_key参数，父类authentication中不接受public_key参数，所以要pop掉
        # TODO:需要优化各backend的authenticate方法，django进行调用前会检测各authenticate的参数
        kwargs.pop('public_key', None)
        return super().authenticate(*args, *kwargs)


class RadiusBackend(CreateUserMixin, RADIUSBackend):
    pass


class RadiusRealmBackend(CreateUserMixin, RADIUSRealmBackend):
    pass
