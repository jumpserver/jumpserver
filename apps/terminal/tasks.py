# -*- coding: utf-8 -*-
#

import os
import subprocess
import datetime

from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from django.core.files.storage import default_storage

from common.utils import get_log_keep_day
from ops.celery.decorator import (
    register_as_period_task, after_app_ready_start, after_app_shutdown_clean_periodic
)
from .models import Status, Session, Command
from .backends import server_replay_storage
from .utils import find_session_replay_local


CACHE_REFRESH_INTERVAL = 10
RUNNING = False
logger = get_task_logger(__name__)


@shared_task
@register_as_period_task(interval=3600)
@after_app_ready_start
@after_app_shutdown_clean_periodic
def delete_terminal_status_period():
    yesterday = timezone.now() - datetime.timedelta(days=1)
    Status.objects.filter(date_created__lt=yesterday).delete()


@shared_task
@register_as_period_task(interval=600)
@after_app_ready_start
@after_app_shutdown_clean_periodic
def clean_orphan_session():
    active_sessions = Session.objects.filter(is_finished=False)
    for session in active_sessions:
        if session.is_active():
            continue
        session.is_finished = True
        session.date_end = timezone.now()
        session.save()


@shared_task
@register_as_period_task(interval=3600*24)
@after_app_ready_start
@after_app_shutdown_clean_periodic
def clean_expired_session_period():
    logger.info("Start clean expired session record, commands and replay")
    days = get_log_keep_day('TERMINAL_SESSION_KEEP_DURATION')
    expire_date = timezone.now() - timezone.timedelta(days=days)
    expired_sessions = Session.objects.filter(date_start__lt=expire_date)
    timestamp = expire_date.timestamp()
    expired_commands = Command.objects.filter(timestamp__lt=timestamp)
    replay_dir = os.path.join(default_storage.base_location, 'replay')

    expired_sessions.delete()
    logger.info("Clean session item done")
    expired_commands.delete()
    logger.info("Clean session command done")
    command = "find %s -mtime +%s -name '*.gz' -exec rm -f {} \\;" % (
        replay_dir, days
    )
    subprocess.call(command, shell=True)
    command = "find %s -type d -empty -delete;" % replay_dir
    subprocess.call(command, shell=True)
    logger.info("Clean session replay done")


@shared_task
def upload_session_replay_to_external_storage(session_id):
    logger.info(f'Start upload session to external storage: {session_id}')
    session = Session.objects.filter(id=session_id).first()
    if not session:
        logger.error(f'Session db item not found: {session_id}')
        return
    local_path, foobar = find_session_replay_local(session)
    if not local_path:
        logger.error(f'Session replay not found, may be upload error: {local_path}')
        return
    abs_path = default_storage.path(local_path)
    remote_path = session.get_rel_replay_path()
    ok, err = server_replay_storage.upload(abs_path, remote_path)
    if not ok:
        logger.error(f'Session replay upload to external error: {err}')
        return
    try:
        default_storage.delete(local_path)
    except:
        pass
    return
