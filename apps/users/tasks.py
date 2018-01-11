# -*- coding: utf-8 -*-
#

from celery import shared_task
from .utils import write_login_log


@shared_task
def write_login_log_async(*args, **kwargs):
    write_login_log(*args, **kwargs)

