# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext as _
from django.contrib.auth import authenticate

from common.utils import (
    get_ip_city, get_object_or_none, validate_ip
)
from users.models import User
from . import errors


def check_user_valid(**kwargs):
    password = kwargs.pop('password', None)
    public_key = kwargs.pop('public_key', None)
    username = kwargs.pop('username', None)
    request = kwargs.get('request')

    user = authenticate(request, username=username,
                        password=password, public_key=public_key)
    if not user:
        return None, errors.reason_password_failed
    elif user.is_expired:
        return None, errors.reason_user_inactive
    elif not user.is_active:
        return None, errors.reason_user_inactive
    elif user.password_has_expired:
        return None, errors.reason_password_expired

    return user, ''
