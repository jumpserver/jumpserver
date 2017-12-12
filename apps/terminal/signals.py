# -*- coding: utf-8 -*-
#
import threading
import time

from django.core.cache import cache
from django.dispatch import Signal, receiver
from django.db.utils import ProgrammingError, OperationalError

from common.utils import get_logger
from .const import ASSETS_CACHE_KEY, USERS_CACHE_KEY, SYSTEM_USER_CACHE_KEY

RUNNING = False
logger = get_logger(__file__)

on_app_ready = Signal()


@receiver(on_app_ready)
def on_app_ready_set_cache(sender, **kwargs):
    from .utils import get_session_asset_list, get_session_user_list, \
        get_session_system_user_list
    global RUNNING

    def set_cache():
        while True:
            try:
                assets = get_session_asset_list()
                users = get_session_user_list()
                system_users = get_session_system_user_list()

                cache.set(ASSETS_CACHE_KEY, assets)
                cache.set(USERS_CACHE_KEY, users)
                cache.set(SYSTEM_USER_CACHE_KEY, system_users)
            except (ProgrammingError, OperationalError):
                pass
            finally:
                time.sleep(10)
    if RUNNING:
        return
    threads = []
    thread = threading.Thread(target=set_cache)
    threads.append(thread)

    logger.debug("Receive app ready signal: set cache task start")
    for t in threads:
        t.daemon = True
        t.start()
        RUNNING = True
