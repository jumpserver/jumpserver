import datetime
from collections import defaultdict

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext_noop

from accounts.const import AutomationTypes
from accounts.tasks.common import quickstart_automation_by_snapshot
from common.const.crontab import CRONTAB_AT_AM_THREE
from common.utils import get_logger, get_object_or_none, get_log_keep_day
from common.utils.lock import DistributedLock
from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_org, tmp_to_root_org

logger = get_logger(__file__)

INTERRUPTED_TASK_CHECK_INTERVAL = 600
INTERRUPTED_TASK_START_GRACE = 600
INTERRUPTED_TASK_CONFIRM_SECONDS = 600
INTERRUPTED_TASK_CACHE_TIMEOUT = 3600
INTERRUPTED_TASK_CACHE_PREFIX = 'account_automation:missing:'
INTERRUPTED_TASK_LOCK_NAME = 'account-automation:recover-interrupted'


def task_activity_callback(self, pid, trigger, tp, *args, **kwargs):
    model = AutomationTypes.get_type_model(tp)
    with tmp_to_root_org():
        instance = get_object_or_none(model, pk=pid)
    if not instance:
        return
    if not instance.latest_execution:
        return
    resource_ids = instance.latest_execution.get_all_asset_ids()
    return resource_ids, instance.org_id


@shared_task(
    queue='ansible',
    verbose_name=_('Account execute automation'),
    activity_callback=task_activity_callback,
    description=_(
        """Unified execution entry for account automation tasks: when the system performs tasks 
        such as account push, password change, account verification, account collection, 
        and gateway account verification, all tasks are executed through this unified entry"""
    )
)
def execute_account_automation_task(pid, trigger, tp):
    model = AutomationTypes.get_type_model(tp)
    with tmp_to_root_org():
        instance = get_object_or_none(model, pk=pid)
    if not instance:
        logger.error("No automation task found: {}".format(pid))
        return
    with tmp_to_org(instance.org):
        instance.execute(trigger)


def record_task_activity_callback(self, record_ids, *args, **kwargs):
    from accounts.models import ChangeSecretRecord
    with tmp_to_root_org():
        records = ChangeSecretRecord.objects.filter(id__in=record_ids)
    if not records:
        return
    resource_ids = [str(i.id) for i in records]
    org_id = records[0].execution.org_id
    return resource_ids, org_id


@shared_task(
    queue='ansible',
    verbose_name=_('Execute automation record'),
    activity_callback=record_task_activity_callback,
    description=_(
        """When manually executing password change records, this task is used"""
    )
)
def execute_automation_record_task(record_ids, tp):
    from accounts.models import ChangeSecretRecord
    task_name = gettext_noop('Execute automation record')

    with tmp_to_root_org():
        records = ChangeSecretRecord.objects.filter(id__in=record_ids).order_by('-date_updated')

    if not records:
        logger.error(f'No automation record found: {record_ids}')
        return

    seen_accounts = set()
    unique_records = []
    for rec in records:
        acct = str(rec.account_id)
        if acct not in seen_accounts:
            seen_accounts.add(acct)
            unique_records.append(rec)

    exec_groups = defaultdict(list)
    for rec in unique_records:
        exec_groups[rec.execution_id].append(rec)

    for __, group in exec_groups.items():
        latest_rec = group[0]
        snapshot = getattr(latest_rec.execution, 'snapshot', {}) or {}

        record_map = {f"{r.asset_id}-{r.account_id}": str(r.id) for r in group}
        assets = [str(r.asset_id) for r in group]
        accounts = [str(r.account_id) for r in group]

        task_snapshot = {
            'params': {},
            'record_map': record_map,
            'secret': latest_rec.new_secret,
            'secret_type': snapshot.get('secret_type'),
            'assets': assets,
            'accounts': accounts,
        }

        with tmp_to_org(latest_rec.execution.org_id):
            quickstart_automation_by_snapshot(task_name, tp, task_snapshot)


def _get_active_celery_tasks():
    from ops.celery import app

    try:
        active_workers = app.control.inspect(timeout=2).active()
    except Exception:
        logger.exception('Inspect active Celery tasks failed')
        return None

    # None means that no worker replied. Treat it as an unavailable inspection,
    # not as proof that every running task has disappeared.
    if not active_workers:
        logger.warning(
            'Skip interrupted account task check: no Celery worker replied'
        )
        return None

    active_task_ids = set()
    for tasks in active_workers.values():
        for task in tasks or []:
            task_id = task.get('id')
            if task_id:
                active_task_ids.add(str(task_id))
    return active_task_ids, set(active_workers)


def _missing_task_confirmed(execution_id, now):
    key = f'{INTERRUPTED_TASK_CACHE_PREFIX}{execution_id}'
    try:
        first_missing_at = cache.get(key)
        if first_missing_at is None:
            cache.set(
                key, now.timestamp(), INTERRUPTED_TASK_CACHE_TIMEOUT
            )
            return False
        return (
            now.timestamp() - float(first_missing_at)
            >= INTERRUPTED_TASK_CONFIRM_SECONDS
        )
    except Exception:
        # Do not recover based on a single observation when the debounce store
        # itself is unavailable.
        logger.exception(
            'Check interrupted task debounce failed: execution=%s',
            execution_id,
        )
        return False


def _clear_missing_task_marker(execution_id):
    try:
        cache.delete(f'{INTERRUPTED_TASK_CACHE_PREFIX}{execution_id}')
    except Exception:
        logger.exception(
            'Clear interrupted task debounce failed: execution=%s',
            execution_id,
        )


@shared_task(
    verbose_name=_('Recover interrupted account automation tasks'),
    description=_(
        """Periodically reconcile account automation executions whose Celery
        worker was forcibly terminated before task state and secret records
        could be written back"""
    ),
)
@register_as_period_task(interval=INTERRUPTED_TASK_CHECK_INTERVAL)
def recover_interrupted_account_automation_tasks():
    lock = DistributedLock(INTERRUPTED_TASK_LOCK_NAME)
    try:
        acquired = lock.acquire(blocking=False)
    except Exception:
        logger.exception(
            'Acquire interrupted account task recovery lock failed'
        )
        return

    if not acquired:
        logger.info(
            'Skip interrupted account task recovery: another check is running'
        )
        return

    try:
        _recover_interrupted_account_automation_tasks()
    finally:
        try:
            lock.release()
        except Exception:
            logger.exception(
                'Release interrupted account task recovery lock failed'
            )


def _recover_interrupted_account_automation_tasks():
    from accounts.automations.recovery import (
        finalize_interrupted_execution,
    )
    from accounts.models import AutomationExecution
    from common.const import Status
    from ops.models import CeleryTaskExecution

    now = timezone.now()
    active_statuses = [Status.pending, Status.running]
    automation_types = list(AutomationTypes.values)

    with tmp_to_root_org():
        executions = list(
            AutomationExecution.objects.filter(
                status__in=active_statuses,
                type__in=automation_types,
            ).only(
                'id', 'status', 'date_created', 'date_start', 'snapshot',
            )
        )

    if not executions:
        return

    owner_task_ids = {
        str(execution.id): str(
            (execution.snapshot or {}).get('celery_task_id')
            or execution.id
        )
        for execution in executions
    }
    celery_executions = {
        str(item.id): item
        for item in CeleryTaskExecution.objects.filter(
            id__in=set(owner_task_ids.values())
        ).only('id', 'state', 'is_finished')
    }

    # First repair executions for which Celery already has a terminal state.
    # This path does not depend on worker inspection.
    pending_inspection = []
    for execution in executions:
        owner_task_id = owner_task_ids[str(execution.id)]
        celery_execution = celery_executions.get(owner_task_id)
        if celery_execution and (
                celery_execution.is_finished
                or celery_execution.state in {
                    'SUCCESS', 'FAILURE', 'REVOKED',
                }
        ):
            if celery_execution.state == 'REVOKED':
                execution_status = Status.canceled
                reason = (
                    'Task was forcibly terminated before completion; '
                    'the remote secret state may be unknown.'
                )
            else:
                execution_status = Status.error
                reason = (
                    'Celery task ended before the automation result was '
                    'written back; the remote secret state may be unknown.'
                )
            finalize_interrupted_execution(
                execution.id, reason, status=execution_status
            )
            _clear_missing_task_marker(execution.id)
            continue
        pending_inspection.append(execution)

    if not pending_inspection:
        return

    active_tasks = _get_active_celery_tasks()
    if active_tasks is None:
        return
    active_task_ids, responding_workers = active_tasks

    stale_before = now - datetime.timedelta(
        seconds=INTERRUPTED_TASK_START_GRACE
    )
    total_timeout = int(
        getattr(settings, 'ANSIBLE_AUTOMATION_TOTAL_TIMEOUT', 21600)
        or 0
    )
    unavailable_worker_stale_before = (
        now - datetime.timedelta(seconds=total_timeout + 600)
        if total_timeout > 0
        else None
    )
    reason = (
        'Celery task disappeared after its worker was forcibly terminated; '
        'the remote secret state may be unknown.'
    )
    for execution in pending_inspection:
        started_at = execution.date_start or execution.date_created
        if started_at > stale_before:
            continue

        execution_id = str(execution.id)
        owner_task_id = owner_task_ids[execution_id]
        if owner_task_id in active_task_ids:
            _clear_missing_task_marker(execution_id)
            continue

        # inspect() can return only a subset of workers during a network
        # partition. Absence is authoritative only when the worker that owns
        # this task replied. If that worker is unavailable, wait until the
        # automation's own hard deadline has elapsed before recovery.
        snapshot = execution.snapshot or {}
        owner_worker = snapshot.get('celery_worker_hostname')
        owner_worker_replied = (
            owner_worker and owner_worker in responding_workers
        )
        if not owner_worker_replied and (
                unavailable_worker_stale_before is None
                or started_at > unavailable_worker_stale_before
        ):
            _clear_missing_task_marker(execution_id)
            continue
        if not _missing_task_confirmed(execution_id, now):
            continue

        recovered = finalize_interrupted_execution(
            execution.id, reason, status=Status.canceled
        )
        if recovered:
            CeleryTaskExecution.objects.filter(
                id=owner_task_id,
                is_finished=False,
            ).update(
                state='REVOKED',
                is_finished=True,
                date_finished=now,
            )
        _clear_missing_task_marker(execution_id)


@shared_task(
    verbose_name=_('Clean change secret and push record period'),
    description=_(
        """The system will periodically clean up unnecessary password change and push records, 
        including their associated change tasks, execution logs, assets, and accounts. When any 
        of these associated items are deleted, the corresponding password change and push records 
        become invalid. Therefore, to maintain a clean and efficient database, the system will 
        clean up expired records at 2 a.m daily, based on the interval specified by 
        PERM_EXPIRED_CHECK_PERIODIC in the config.txt configuration file. This periodic cleanup 
        mechanism helps free up storage space and enhances the security and overall performance 
        of data management"""
    )
)
@register_as_period_task(crontab=CRONTAB_AT_AM_THREE)
def clean_change_secret_and_push_record_period():
    from accounts.models import ChangeSecretRecord, PushSecretRecord
    print('Start clean change secret and push record period')
    with tmp_to_root_org():
        now = timezone.now()
        days = get_log_keep_day('ACCOUNT_CHANGE_SECRET_RECORD_KEEP_DAYS')
        expired_time = now - datetime.timedelta(days=days)

        null_related_q = Q(execution__isnull=True) | Q(asset__isnull=True) | Q(account__isnull=True)
        expired_q = Q(date_updated__lt=expired_time)

        ChangeSecretRecord.objects.filter(null_related_q).delete()
        ChangeSecretRecord.objects.filter(expired_q).delete()

        PushSecretRecord.objects.filter(null_related_q).delete()
        PushSecretRecord.objects.filter(expired_q).delete()
