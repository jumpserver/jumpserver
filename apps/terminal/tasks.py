# -*- coding: utf-8 -*-
#
import threading
import time

from celery import shared_task
from django.core.cache import cache

from .models import Session


ASSETS_CACHE_KEY = "terminal__session__assets"
USERS_CACHE_KEY = "terminal__session__users"
SYSTEM_USER_CACHE_KEY = "terminal__session__system_users"
CACHE_REFRESH_INTERVAL = 10
RUNNING = False


# Todo: 定期清理上报history
@shared_task
def clean_terminal_history():
    pass


def get_session_asset_list():
    return set(list(Session.objects.values_list('asset', flat=True)))


def get_session_user_list():
    return set(list(Session.objects.values_list('user', flat=True)))


def get_session_system_user_list():
    return set(list(Session.objects.values_list('system_user', flat=True)))


def set_cache():
    while True:
        assets = get_session_asset_list()
        users = get_session_user_list()
        system_users = get_session_system_user_list()

        cache.set(ASSETS_CACHE_KEY, assets)
        cache.set(USERS_CACHE_KEY, users)
        cache.set(SYSTEM_USER_CACHE_KEY, system_users)
        time.sleep(10)


def main():
    global RUNNING
    if RUNNING:
        return
    threads = []
    thread = threading.Thread(target=set_cache)
    threads.append(thread)

    for t in threads:
        t.daemon = True
        t.start()
        RUNNING = True

main()
