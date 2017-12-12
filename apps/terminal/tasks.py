# -*- coding: utf-8 -*-
#
import time

from celery import shared_task
from django.core.cache import cache
from django.db.utils import ProgrammingError, OperationalError

from .models import Session



CACHE_REFRESH_INTERVAL = 10
RUNNING = False


# Todo: 定期清理上报history
@shared_task
def clean_terminal_history():
    pass






