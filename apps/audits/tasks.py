# -*- coding: utf-8 -*-
#
import datetime
import os
import shutil

from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from django.utils._os import safe_join
from django.utils.translation import gettext_lazy as _
from django.db.models import Min

from common.const.crontab import CRONTAB_AT_AM_TWO, CRONTAB_AT_AM_THREE
from common.storage.ftp_file import FTPFileStorageHandler
from common.utils import get_log_keep_day, get_logger
from common.utils.safe import find_and_delete_empty_dirs, find_and_delete_files, truncate_file
from ops.celery.decorator import register_as_period_task
from ops.models import CeleryTaskExecution
from orgs.utils import tmp_to_root_org
from terminal.backends import server_replay_storage
from terminal.models import Session, Command
from .models import UserLoginLog, OperateLog, FTPLog, ActivityLog, PasswordChangeLog, StorageReclamationLog

logger = get_logger(__name__)


def clean_login_log_period():
    now = timezone.now()
    days = get_log_keep_day('LOGIN_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    UserLoginLog.objects.filter(datetime__lt=expired_day).delete()


def clean_operation_log_period():
    now = timezone.now()
    days = get_log_keep_day('OPERATE_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    OperateLog.objects.filter(datetime__lt=expired_day).delete()


def clean_password_change_log_period():
    now = timezone.now()
    days = get_log_keep_day('PASSWORD_CHANGE_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    PasswordChangeLog.objects.filter(datetime__lt=expired_day).delete()
    logger.info("Clean password change log done")


def clean_activity_log_period():
    now = timezone.now()
    days = get_log_keep_day('ACTIVITY_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    ActivityLog.objects.filter(datetime__lt=expired_day).delete()


def clean_ftp_log_period():
    now = timezone.now()
    days = get_log_keep_day('FTP_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    file_store_dir = safe_join(default_storage.base_location, FTPLog.upload_to)
    FTPLog.objects.filter(date_start__lt=expired_day).delete()
    find_and_delete_files(file_store_dir, mtime_days=days)
    find_and_delete_empty_dirs(file_store_dir)
    logger.info("Clean FTP file done")


def clean_celery_tasks_period():
    logger.debug("Start clean celery task history")
    expire_days = get_log_keep_day('TASK_LOG_KEEP_DAYS')
    days_ago = timezone.now() - timezone.timedelta(days=expire_days)
    tasks = CeleryTaskExecution.objects.filter(date_start__lt=days_ago)
    tasks.delete()
    tasks = CeleryTaskExecution.objects.filter(date_start__isnull=True)
    tasks.delete()
    find_and_delete_files(settings.CELERY_LOG_DIR, name_pattern="*.log", mtime_days=expire_days)
    celery_log_path = safe_join(settings.LOG_DIR, 'celery.log')
    truncate_file(celery_log_path)


def batch_delete(queryset, batch_size=3000):
    model = queryset.model
    count = queryset.count()
    with transaction.atomic():
        for i in range(0, count, batch_size):
            pks = queryset[i:i + batch_size].values_list('id', flat=True)
            model.objects.filter(id__in=list(pks)).delete()


def delete_expired_commands_by_day(keep_days, direct_delete_limit=10000, batch_size=3000):
    ''' Delete expired commands by day. '''
    expire_timestamp = (timezone.now() - timezone.timedelta(days=keep_days)).timestamp()
    expired_queryset = Command.objects.order_by().filter(timestamp__lt=expire_timestamp)
    min_timestamp = expired_queryset.aggregate(min_ts=Min('timestamp')).get('min_ts')
    logger.info('Min date for expired commands: %s', datetime.datetime.fromtimestamp(min_timestamp))
    if min_timestamp is None:
        return

    tz = timezone.get_current_timezone()
    current_day = datetime.datetime.fromtimestamp(min_timestamp, tz=tz).date()
    expire_datetime = datetime.datetime.fromtimestamp(expire_timestamp, tz=tz)
    expire_day = expire_datetime.date()
    logger.info('Start clean expired session command by day, expire day: %s', expire_day)

    while current_day <= expire_day:
        day_start = datetime.datetime.combine(current_day, datetime.time.min, tzinfo=tz)
        next_day = day_start + datetime.timedelta(days=1)

        day_start_ts = day_start.timestamp()
        day_end_ts = min(next_day.timestamp(), expire_timestamp)
        if day_start_ts >= day_end_ts:
            current_day += datetime.timedelta(days=1)
            continue

        logger.info('Clean session command for day: %s', current_day)
        day_queryset = Command.objects.order_by().filter(timestamp__gte=day_start_ts, timestamp__lt=day_end_ts)
        day_count = day_queryset.count()
        logger.info('Start clean session command for %s, count=%s', current_day, day_count)
        if day_count == 0:
            current_day += datetime.timedelta(days=1)
            continue

        if day_count <= direct_delete_limit:
            logger.info('Direct delete session command for %s, count=%s', current_day, day_count)
            day_queryset.delete()
        else:
            logger.info('Batch delete session command for %s, count=%s', current_day, day_count)
            batch_delete(day_queryset, batch_size=batch_size)

        logger.info(
            "Clean session command done for %s, count=%s, mode=%s",
            current_day,
            day_count,
            'direct' if day_count <= direct_delete_limit else 'batch',
        )
        current_day += datetime.timedelta(days=1)


def remove_files_by_days(root_path, days, file_types=None):
    if file_types is None:
        file_types = ['.json', '.tar', '.gz', '.mp4']
    expire_date = timezone.now() - timezone.timedelta(days=days)
    timestamp = expire_date.timestamp()
    for root, dirs, files in os.walk(root_path):
        rm_files = []
        for file in files:
            if any(file.endswith(file_type) for file_type in file_types):
                file_path = os.path.join(root, file)
                if os.path.getmtime(file_path) <= timestamp:
                    rm_files.append(file_path)
        for file in rm_files:
            try:
                os.remove(file)
            except Exception as e:
                logger.error(f"Remove file {file} error: {e}")


def clean_expired_session_period():
    logger.info("Start clean expired session record, commands and replay")
    days = get_log_keep_day('TERMINAL_SESSION_KEEP_DURATION')

    expire_date = timezone.now() - timezone.timedelta(days=days)
    expired_sessions = Session.objects.filter(date_start__lt=expire_date)

    logger.info("Start clean session item")
    batch_delete(expired_sessions)
    logger.info("Clean session item done")

    logger.info("Start clean session command")
    delete_expired_commands_by_day(keep_days=days)
    logger.info("Clean session command done")

    logger.info("Start clean session replay")
    replay_dir = safe_join(default_storage.base_location, 'replay')
    remove_files_by_days(replay_dir, days)
    logger.info("Clean session replay files done")

    find_and_delete_empty_dirs(replay_dir)
    logger.info("Clean session replay done")


def _remove_replay_files_for_session(session):
    """Delete all replay files for a session and return deleted file info.
    Returns list of (file_path, file_size) tuples."""
    deleted_files = []
    possible_paths = session.get_all_possible_local_path()

    for local_path in possible_paths:
        abs_path = os.path.join(default_storage.base_location, local_path) \
            if not os.path.isabs(local_path) else local_path
        if not os.path.isfile(abs_path):
            continue
        try:
            file_size = os.path.getsize(abs_path)
            os.remove(abs_path)
            deleted_files.append((abs_path, file_size))
            logger.info('Deleted replay file: %s (%d bytes)', abs_path, file_size)
        except OSError as e:
            logger.error('Failed to delete replay file %s: %s', abs_path, e)

    return deleted_files


def _remove_ftp_file_for_log(ftp_log):
    """Delete the file transfer file for an FTPLog record.
    Returns (file_path, file_size) or (None, 0) if no file found."""
    file_path = ftp_log.filepath
    abs_path = os.path.join(default_storage.base_location, file_path) \
        if not os.path.isabs(file_path) else file_path
    if not os.path.isfile(abs_path):
        return None, 0
    try:
        file_size = os.path.getsize(abs_path)
        os.remove(abs_path)
        logger.info('Deleted FTP file: %s (%d bytes)', abs_path, file_size)
        return abs_path, file_size
    except OSError as e:
        logger.error('Failed to delete FTP file %s: %s', abs_path, e)
        return None, 0


@shared_task(
    verbose_name=_('Reclaim storage by threshold'),
    description=_(
        """If system storage usage exceeds STORAGE_USAGE_THRESHOLD (percentage 0-100),
        delete the oldest session replay files and update session records
        until usage falls below threshold"""
    )
)
@register_as_period_task(crontab=CRONTAB_AT_AM_THREE)
def reclaim_storage_by_threshold():
    """If storage usage exceeds STORAGE_USAGE_THRESHOLD, clean the oldest
    replay files and/or FTP files based on STORAGE_RECLAMATION_TARGETS.
    For each day, both replay and FTP files are cleaned together,
    then disk usage is rechecked before proceeding to the next day."""
    from terminal.const import SessionErrorReason

    threshold_pct = getattr(settings, 'STORAGE_USAGE_THRESHOLD', 0)
    if threshold_pct <= 0 or threshold_pct >= 100:
        return

    base_path = default_storage.base_location
    usage = shutil.disk_usage(base_path)
    current_pct = usage.used / usage.total * 100

    if current_pct <= threshold_pct:
        return

    targets = getattr(settings, 'STORAGE_RECLAMATION_TARGETS', [])
    if not targets:
        return

    logger.info(
        'System storage used %.1f%% exceeds threshold %d%%, start reclaiming: %s',
        current_pct, threshold_pct, targets
    )

    # Find the oldest day across all enabled targets
    oldest_days = 0
    if 'session_replay' in targets:
        oldest_session = Session.objects.filter(has_replay=True).order_by('date_start').first()
        if oldest_session and oldest_session.date_start:
            oldest_days = (timezone.now() - oldest_session.date_start).days
    if 'file_transfer' in targets:
        oldest_ftp = FTPLog.objects.filter(has_file=True).order_by('date_start').first()
        if oldest_ftp and oldest_ftp.date_start:
            ftp_oldest_days = (timezone.now() - oldest_ftp.date_start).days
            oldest_days = max(oldest_days, ftp_oldest_days)

    if oldest_days <= 0:
        logger.info('No reclaimable data found')
        return

    logger.info('Oldest reclaimable data dates back %d days, starting reclamation', oldest_days)

    for days in range(oldest_days, 0, -1):
        expire_date = timezone.now() - timezone.timedelta(days=days)

        if 'session_replay' in targets:
            _clean_replays_for_day(expire_date, days)

        if 'file_transfer' in targets:
            _clean_ftp_files_for_day(expire_date, days)

        usage = shutil.disk_usage(base_path)
        current_pct = usage.used / usage.total * 100

        if current_pct <= threshold_pct:
            logger.info(
                'System storage used %.1f%% within threshold %d%%, reclamation done',
                current_pct, threshold_pct
            )
            break

    find_and_delete_empty_dirs(safe_join(default_storage.base_location, 'replay'))
    usage = shutil.disk_usage(base_path)
    final_pct = usage.used / usage.total * 100
    logger.info(
        'Storage reclamation complete, system used: %.1f%% (%d / %d MB)',
        final_pct, usage.used // 1024 // 1024, usage.total // 1024 // 1024
    )


def _clean_replays_for_day(expire_date, days):
    """Delete replay files for sessions older than expire_date."""
    from terminal.const import SessionErrorReason

    sessions = Session.objects.filter(
        has_replay=True, date_start__lt=expire_date
    )
    if not sessions.exists():
        return

    logger.info(
        'Cleaning replay files for %d sessions older than %d days',
        sessions.count(), days
    )

    with transaction.atomic():
        for session in sessions.iterator():
            deleted_files = _remove_replay_files_for_session(session)
            if not deleted_files:
                continue

            session.has_replay = False
            session.error_reason = SessionErrorReason.replay_cleaned
            session.replay_size = 0
            session.save(update_fields=['has_replay', 'error_reason', 'replay_size'])

            for file_path, file_size in deleted_files:
                StorageReclamationLog.objects.create(
                    session_id=str(session.id),
                    target_type='session_replay',
                    file_path=file_path,
                    file_size=file_size,
                )


def _clean_ftp_files_for_day(expire_date, days):
    """Delete FTP transfer files for records older than expire_date."""
    ftp_logs = FTPLog.objects.filter(
        has_file=True, date_start__lt=expire_date
    )
    if not ftp_logs.exists():
        return

    logger.info(
        'Cleaning FTP files for %d records older than %d days',
        ftp_logs.count(), days
    )

    with transaction.atomic():
        for ftp_log in ftp_logs.iterator():
            file_path, file_size = _remove_ftp_file_for_log(ftp_log)
            if file_path is None:
                continue

            ftp_log.has_file = False
            ftp_log.save(update_fields=['has_file'])

            StorageReclamationLog.objects.create(
                session_id=str(ftp_log.id),
                target_type='file_transfer',
                file_path=file_path,
                file_size=file_size,
            )


@shared_task(
    verbose_name=_('Clean audits session task log'),
    description=_(
        """Since the system generates login logs, operation logs, file upload logs, activity 
        logs, Celery execution logs, session recordings, command records, and password change 
        logs, it will perform cleanup of records that exceed the time limit according to the 
        'Tasks - Regular clean-up' in the system settings at 2 a.m daily"""
    )
)
@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
def clean_audits_log_period():
    print("Start clean audit session task log")
    with tmp_to_root_org():
        clean_login_log_period()
        clean_operation_log_period()
        clean_ftp_log_period()
        clean_activity_log_period()
        clean_celery_tasks_period()
        clean_expired_session_period()
        clean_password_change_log_period()


@shared_task(
    verbose_name=_('Upload FTP file to external storage'),
    description=_(
        """If SERVER_REPLAY_STORAGE is configured, files uploaded through file management will be 
        synchronized to external storage"""
    )
)
def upload_ftp_file_to_external_storage(ftp_log_id, file_name):
    logger.info(f'Start upload FTP file record to external storage: {ftp_log_id} - {file_name}')
    ftp_log = FTPLog.objects.filter(id=ftp_log_id).first()
    if not ftp_log:
        logger.error(f'FTP db item not found: {ftp_log_id}')
        return
    ftp_storage = FTPFileStorageHandler(ftp_log)
    local_path, url = ftp_storage.find_local()
    if not local_path:
        logger.error(f'FTP file record not found, may be upload error. file name: {file_name}')
        return
    abs_path = default_storage.path(local_path)
    ok, err = server_replay_storage.upload(abs_path, ftp_log.filepath)
    if not ok:
        logger.error(f'Session file record upload to external error: {err}')
        return
    try:
        default_storage.delete(local_path)
    except:
        pass
    return