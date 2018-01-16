# -*- coding: utf-8 -*-
#
from celery import shared_task
from django.core.cache import cache
from django.db.utils import ProgrammingError, OperationalError

from common.utils import get_logger
from common.celery import after_app_ready_start, register_as_period_task, \
    after_app_shutdown_clean
from .const import ASSETS_CACHE_KEY, USERS_CACHE_KEY, SYSTEM_USER_CACHE_KEY

RUNNING = False
logger = get_logger(__file__)


def set_session_info_cache():
    logger.debug("")
    from .utils import get_session_asset_list, get_session_user_list, \
        get_session_system_user_list

    try:
        assets = get_session_asset_list()
        users = get_session_user_list()
        system_users = get_session_system_user_list()

        cache.set(ASSETS_CACHE_KEY, assets)
        cache.set(USERS_CACHE_KEY, users)
        cache.set(SYSTEM_USER_CACHE_KEY, system_users)
    except (ProgrammingError, OperationalError):
        pass
