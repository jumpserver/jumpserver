# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext as _
from django.contrib.auth import authenticate

from common.utils import get_ip_city, get_object_or_none, validate_ip
from users.models import User
from . import const


def write_login_log(*args, **kwargs):
    from audits.models import UserLoginLog
    default_city = _("Unknown")
    ip = kwargs.get('ip') or ''
    if not (ip and validate_ip(ip)):
        ip = ip[:15]
        city = default_city
    else:
        city = get_ip_city(ip) or default_city
    kwargs.update({'ip': ip, 'city': city})
    UserLoginLog.objects.create(**kwargs)


def check_user_valid(**kwargs):
    password = kwargs.pop('password', None)
    public_key = kwargs.pop('public_key', None)
    email = kwargs.pop('email', None)
    username = kwargs.pop('username', None)

    if username:
        user = get_object_or_none(User, username=username)
    elif email:
        user = get_object_or_none(User, email=email)
    else:
        user = None

    if user is None:
        return None, const.user_not_exist
    elif not user.is_valid:
        return None, const.user_invalid
    elif user.password_has_expired:
        return None, const.password_expired

    if password and authenticate(username=username, password=password):
        return user, ''

    if public_key and user.public_key:
        public_key_saved = user.public_key.split()
        if len(public_key_saved) == 1:
            if public_key == public_key_saved[0]:
                return user, ''
        elif len(public_key_saved) > 1:
            if public_key == public_key_saved[1]:
                return user, ''
    return None, const.password_failed
