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
    email = kwargs.pop('email', None)
    username = kwargs.pop('username', None)
    request = kwargs.get('request')

    if username:
        user = get_object_or_none(User, username=username)
    elif email:
        user = get_object_or_none(User, email=email)
    else:
        user = None

    if user is None:
        return None, errors.reason_user_not_exist
    elif user.is_expired:
        return None, errors.reason_user_inactive
    elif not user.is_active:
        return None, errors.reason_user_inactive
    elif user.password_has_expired:
        return None, errors.reason_password_expired

    if password or public_key:
        user = authenticate(request, username=username,
                            password=password, public_key=public_key)
        if user:
            return user, ''
    return None, errors.reason_password_failed
