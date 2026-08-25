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
from settings.const import NAS_MOUNT_PATH
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
    if min_timestamp is None:
        logger.info('No expired session command found')
        return
    logger.info('Min date for expired commands: %s', datetime.datetime.fromtimestamp(min_timestamp))
    

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


def _archive_or_delete_file(abs_path, action, nas_mount_path=None):
    """Archive a local file or directory tree to NAS (in archive mode) and then
    delete it locally. Returns (size, error). If archiving fails, local data is kept.
    Directory trees are mirrored to NAS under the same relative path, then removed."""
    is_dir = os.path.isdir(abs_path)
    if not is_dir and not os.path.isfile(abs_path):
        return None
    try:
        if action == 'archive':
            rel_path = os.path.relpath(abs_path, default_storage.base_location)
            nas_target = os.path.join(nas_mount_path, rel_path)
            if is_dir:
                nas_parent = os.path.dirname(nas_target)
                if not os.path.isdir(nas_parent):
                    os.makedirs(nas_parent, exist_ok=True)
                if os.path.isdir(nas_target):
                    shutil.rmtree(nas_target)
                shutil.copytree(abs_path, nas_target)
            else:
                nas_target_dir = os.path.dirname(nas_target)
                if not os.path.isdir(nas_target_dir):
                    os.makedirs(nas_target_dir, exist_ok=True)
                shutil.copy2(abs_path, nas_target)
            logger.info('Archived: %s -> %s', abs_path, nas_target)
        if is_dir:
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)
        logger.info('Deleted local: %s', abs_path)
        return None
    except OSError as e:
        logger.error('Failed to %s %s: %s', action, abs_path, e)
        return e


def _process_replay_files_for_session(session, action, nas_mount_path=None):
    """Process (archive or delete) the whole replay directory of a session, or fall back
    to the per-file possible list when the directory does not exist.
    Returns (processed_count, errors)."""
    processed = 0
    errors = []

    rel_dir = session.get_replay_dir_relative_path()
    abs_dir = os.path.join(default_storage.base_location, session.upload_to, rel_dir)
    if os.path.isdir(abs_dir):
        err = _archive_or_delete_file(abs_dir, action, nas_mount_path)
        if err:
            errors.append((abs_dir, str(err)))
        else:
            processed += 1
        return processed, errors

    # Directory not present: fall back to processing the possible file recordings
    for local_path in session.get_all_possible_local_path():
        abs_path = os.path.join(default_storage.base_location, local_path) \
            if not os.path.isabs(local_path) else local_path
        if not os.path.isfile(abs_path):
            continue
        err = _archive_or_delete_file(abs_path, action, nas_mount_path)
        if err:
            errors.append((abs_path, str(err)))
        else:
            processed += 1
    return processed, errors


def _process_ftp_file_for_log(ftp_log, action, nas_mount_path=None):
    """Process (archive or delete) the file transfer file for an FTPLog record.
    Returns (processed_count, errors)."""
    file_path = ftp_log.filepath
    abs_path = os.path.join(default_storage.base_location, file_path) \
        if not os.path.isabs(file_path) else file_path
    if not os.path.isfile(abs_path):
        return 0, []
    err = _archive_or_delete_file(abs_path, action, nas_mount_path)
    if err:
        return 0, [(abs_path, str(err))]
    return 1, []


RECLAMATION_METHODS = {
    'delete_day': ('delete', 1),
    'archive_day': ('archive', 1),
    'delete_month': ('delete', 30),
    'archive_month': ('archive', 30),
}


def _parse_reclamation_method(method):
    action, window_days = RECLAMATION_METHODS.get(method, ('delete', 1))
    return action, window_days


def _next_month_start(d):
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1)
    return d.replace(month=d.month + 1)


def _get_clean_window(data_start, window_days):
    """Return (window_start, window_end) for the oldest data point.
    Day granularity (window_days == 1) covers the natural day containing data_start;
    otherwise covers the natural month containing data_start."""
    local_ts = timezone.localtime(data_start)
    local_date = local_ts.date()
    if window_days == 1:
        window_start = timezone.make_aware(
            datetime.datetime.combine(local_date, datetime.time.min)
        )
        window_end = window_start + datetime.timedelta(days=1)
        return window_start, window_end

    month_start = local_date.replace(day=1)
    window_start = timezone.make_aware(
        datetime.datetime.combine(month_start, datetime.time.min)
    )
    window_end = timezone.make_aware(
        datetime.datetime.combine(_next_month_start(month_start), datetime.time.min)
    )
    return window_start, window_end


@shared_task(
    verbose_name=_('Reclaim storage by threshold'),
    description=_(
        'If system storage usage exceeds STORAGE_USAGE_THRESHOLD (percentage 50-95),\n'
        'delete or archive the oldest session replay files and update session records\n'
        'until usage falls below threshold'
    )
)
@register_as_period_task(crontab=CRONTAB_AT_AM_THREE)
def reclaim_storage_by_threshold():
    """If storage usage exceeds STORAGE_USAGE_THRESHOLD, clean the oldest
    replay files and/or FTP files based on STORAGE_RECLAMATION_TARGETS.
    STORAGE_RECLAMATION_METHOD determines both the action (delete/archive)
    and the time window (earliest day/month) to clean in this run."""
    with tmp_to_root_org():
        reclaim_storage_by_threshold_task()

        
def reclaim_storage_by_threshold_task():
    threshold_pct = getattr(settings, 'STORAGE_USAGE_THRESHOLD', 0)
    if threshold_pct <= 0 or threshold_pct >= 100:
        return

    base_path = default_storage.base_location

    # targets = getattr(settings, 'STORAGE_RECLAMATION_TARGETS', [])
    targets = ['session_replay', 'file_transfer']
    if not targets:
        return

    method = getattr(settings, 'STORAGE_RECLAMATION_METHOD', 'delete_day')
    action, window_days = _parse_reclamation_method(method)

    nas_mount_path = None
    if action == 'archive':
        nas_mount_path = NAS_MOUNT_PATH
        from settings.tools.nas_mount import ensure_nas_mounted

        nas_config = {
            'nas_enabled': getattr(settings, 'NAS_ENABLED', False),
            'nas_type': getattr(settings, 'NAS_TYPE', 'nfs'),
            'nas_host': getattr(settings, 'NAS_HOST', ''),
            'nas_port': getattr(settings, 'NAS_PORT', 0),
            'nas_share_name': getattr(settings, 'NAS_SHARE_NAME', ''),
            'nas_mount_path': nas_mount_path,
            'nas_username': getattr(settings, 'NAS_USERNAME', ''),
            'nas_password': getattr(settings, 'NAS_PASSWORD', ''),
        }
        if not ensure_nas_mounted(nas_config, force=True) or not os.path.ismount(nas_mount_path):
            logger.error('NAS mount path not available for archive reclamation: %s', nas_mount_path)
            StorageReclamationLog.objects.create(
                method=method, data_start=None, data_end=None, result='fail'
            )
            raise Exception('NAS mount path not available for archive reclamation')

    usage = shutil.disk_usage(base_path)
    current_pct = usage.used / usage.total * 100

    if current_pct <= threshold_pct:
        return

    logger.info(
        'System storage used %.1f%% exceeds threshold %d%%, start reclaiming (method=%s): %s',
        current_pct, threshold_pct, method, targets
    )

    result = 'success'
    total_errors = []
    # Earliest/latest date actually reclaimed across all windows
    reclaimed_start = None
    reclaimed_end = None
    search_from = None

    while True:
        # Find the oldest data across all enabled targets
        data_start = None
        session_qs = Session.objects.filter(has_replay=True)
        ftp_qs = FTPLog.objects.filter(has_file=True)
        if search_from is not None:
            session_qs = session_qs.filter(date_start__gte=search_from)
            ftp_qs = ftp_qs.filter(date_start__gte=search_from)

        if 'session_replay' in targets:
            oldest_session = session_qs.order_by('date_start').first()
            if oldest_session and oldest_session.date_start:
                data_start = oldest_session.date_start
        if 'file_transfer' in targets:
            oldest_ftp = ftp_qs.order_by('date_start').first()
            if oldest_ftp and oldest_ftp.date_start:
                if data_start is None or oldest_ftp.date_start < data_start:
                    data_start = oldest_ftp.date_start

        if not data_start:
            logger.info('No reclaimable data found')
            break

        window_start, window_end = _get_clean_window(data_start, window_days)
        search_from = window_end

        logger.info(
            'Reclaiming oldest data in [%s, %s) (action=%s, window=%d days)',
            window_start, window_end, action, window_days
        )

        try:
            if 'session_replay' in targets:
                _, errors, c_start, c_end = _clean_replays_in_window(
                    window_start, window_end, action, nas_mount_path
                )
                total_errors.extend(errors)
                if c_start is not None and (reclaimed_start is None or c_start < reclaimed_start):
                    reclaimed_start = c_start
                if c_end is not None and (reclaimed_end is None or c_end > reclaimed_end):
                    reclaimed_end = c_end

            if 'file_transfer' in targets:
                _, errors, c_start, c_end = _clean_ftp_files_in_window(
                    window_start, window_end, action, nas_mount_path
                )
                total_errors.extend(errors)
                if c_start is not None and (reclaimed_start is None or c_start < reclaimed_start):
                    reclaimed_start = c_start
                if c_end is not None and (reclaimed_end is None or c_end > reclaimed_end):
                    reclaimed_end = c_end
        except Exception as e:
            logger.error('Storage reclamation failed: %s', e)
            result = 'fail'
            break

        # After this window, re-check storage usage; continue if still above threshold
        usage = shutil.disk_usage(base_path)
        current_pct = usage.used / usage.total * 100
        if current_pct <= threshold_pct:
            break

    if total_errors:
        result = 'fail'

    find_and_delete_empty_dirs(safe_join(default_storage.base_location, 'replay'))

    if reclaimed_start is not None and reclaimed_end is not None:
        StorageReclamationLog.objects.create(
            method=method,
            data_start=reclaimed_start,
            data_end=reclaimed_end,
            result=result,
        )
    if total_errors:
        raise Exception('Storage reclamation failed with errors')
    usage = shutil.disk_usage(base_path)
    final_pct = usage.used / usage.total * 100
    logger.info(
        'Storage reclamation complete, system used: %.1f%% (%d / %d MB)',
        final_pct, usage.used // 1024 // 1024, usage.total // 1024 // 1024
    )


def _clean_replays_in_window(start_date, end_date, action, nas_mount_path=None):
    """Process (archive or delete) replay files for sessions within [start_date, end_date).
    Returns (processed, errors, cleaned_start, cleaned_end) where cleaned_start/cleaned_end
    are the earliest/latest date_start actually reclaimed in this window (None if none)."""
    from terminal.const import SessionErrorReason

    sessions = Session.objects.filter(
        has_replay=True, date_start__gte=start_date, date_start__lt=end_date
    ).order_by('date_start')
    if not sessions.exists():
        return 0, [], None, None

    logger.info(
        'Processing replay files for %d sessions in [%s, %s) (action=%s)',
        sessions.count(), start_date, end_date, action
    )

    processed = 0
    errors = []
    cleaned_start = None
    cleaned_end = None
    for session in sessions.iterator():
        count, session_errors = _process_replay_files_for_session(
            session, action, nas_mount_path
        )
        errors.extend(session_errors)
        if count == 0:
            continue

        processed += count
        if not session_errors:
            with transaction.atomic():
                session.has_replay = False
                session.error_reason = SessionErrorReason.replay_cleaned
                session.replay_size = 0
                session.save(update_fields=['has_replay', 'error_reason', 'replay_size'])
            if cleaned_start is None or session.date_start < cleaned_start:
                cleaned_start = session.date_start
            if cleaned_end is None or session.date_start > cleaned_end:
                cleaned_end = session.date_start

    return processed, errors, cleaned_start, cleaned_end


def _clean_ftp_files_in_window(start_date, end_date, action, nas_mount_path=None):
    """Process (archive or delete) FTP transfer files for records within [start_date, end_date).
    Returns (processed, errors, cleaned_start, cleaned_end) where cleaned_start/cleaned_end
    are the earliest/latest date_start actually reclaimed in this window (None if none)."""
    ftp_logs = FTPLog.objects.filter(
        has_file=True, date_start__gte=start_date, date_start__lt=end_date
    ).order_by('date_start')
    if not ftp_logs.exists():
        return 0, [], None, None

    logger.info(
        'Processing FTP files for %d records in [%s, %s) (action=%s)',
        ftp_logs.count(), start_date, end_date, action
    )

    processed = 0
    errors = []
    cleaned_start = None
    cleaned_end = None
    for ftp_log in ftp_logs.iterator():
        count, log_errors = _process_ftp_file_for_log(ftp_log, action, nas_mount_path)
        errors.extend(log_errors)
        if count == 0:
            continue

        processed += count
        if not log_errors:
            with transaction.atomic():
                ftp_log.has_file = False
                ftp_log.save(update_fields=['has_file'])
            if cleaned_start is None or ftp_log.date_start < cleaned_start:
                cleaned_start = ftp_log.date_start
            if cleaned_end is None or ftp_log.date_start > cleaned_end:
                cleaned_end = ftp_log.date_start

    return processed, errors, cleaned_start, cleaned_end


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