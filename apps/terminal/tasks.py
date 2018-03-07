# -*- coding: utf-8 -*-
#

import datetime

from celery import shared_task
from django.utils import timezone

from common.celery import register_as_period_task, after_app_ready_start, \
    after_app_shutdown_clean
from .models import Status, Session


CACHE_REFRESH_INTERVAL = 10
RUNNING = False


@shared_task
@register_as_period_task(interval=3600)
@after_app_ready_start
@after_app_shutdown_clean
def delete_terminal_status_period():
    yesterday = timezone.now() - datetime.timedelta(days=3)
    Status.objects.filter(date_created__lt=yesterday).delete()


@shared_task
@register_as_period_task(interval=3600)
@after_app_ready_start
@after_app_shutdown_clean
def clean_orphan_session():
    active_sessions = Session.objects.filter(is_finished=False)
    for session in active_sessions:
        if not session.terminal or not session.terminal.is_active:
            session.is_finished = True
            session.save()
