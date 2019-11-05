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
        return None, errors.reason_password_expired
    elif not user.is_active:
        return None, errors.reason_user_inactive
    elif user.password_has_expired:
        return None, errors.reason_password_expired

    if password:
        user = authenticate(request, username=username, password=password)
        if user:
            return user, ''

    if public_key and user.public_key:
        public_key_saved = user.public_key.split()
        if len(public_key_saved) == 1:
            public_key_saved = public_key_saved[0]
        else:
            public_key_saved = public_key_saved[1]
        if public_key == public_key_saved:
            return user, ''
    return None, errors.reason_password_failed
