# -*- coding: utf-8 -*-
#
from django.core.cache import cache
from .models import Session

from .const import USERS_CACHE_KEY, ASSETS_CACHE_KEY, SYSTEM_USER_CACHE_KEY


def get_session_asset_list():
    return set(list(Session.objects.values_list('asset', flat=True)))


def get_session_user_list():
    return set(list(Session.objects.values_list('user', flat=True)))


def get_session_system_user_list():
    return set(list(Session.objects.values_list('system_user', flat=True)))


def get_user_list_from_cache():
    return cache.get(USERS_CACHE_KEY)


def get_asset_list_from_cache():
    return cache.get(ASSETS_CACHE_KEY)


def get_system_user_list_from_cache():
    return cache.get(SYSTEM_USER_CACHE_KEY)



