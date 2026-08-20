import os
import shutil

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.const import (
    ChangeSecretRecordStatusChoice,
)
from common.const import Status
from common.utils import get_logger
from orgs.utils import tmp_to_root_org

logger = get_logger(__file__)


def _cleanup_interrupted_runtime(execution_id, snapshot):
    if settings.DEBUG_DEV:
        return
    from assets.automations.base.manager import safe_runtime_dir_name

    runtime_dir = os.path.join(
        settings.ANSIBLE_DIR,
        'automations',
        str(snapshot.get('type') or ''),
        '{}_{}'.format(
            safe_runtime_dir_name(snapshot.get('name')),
            execution_id,
        ),
    )
    automation_root = os.path.realpath(os.path.join(
        settings.ANSIBLE_DIR, 'automations'
    ))
    runtime_dir = os.path.realpath(runtime_dir)
    if os.path.commonpath([automation_root, runtime_dir]) != automation_root:
        raise ValueError('Invalid interrupted automation runtime path')
    shutil.rmtree(runtime_dir, ignore_errors=True)


def _increase_summary(summary, key, amount):
    if not amount:
        return
    try:
        current = int(summary.get(key, 0))
    except (TypeError, ValueError):
        current = 0
    summary[key] = current + amount


def finalize_interrupted_execution(
        execution_id, reason, status=Status.canceled
):
    """
    Close an account automation execution whose worker can no longer run its
    normal post_run cleanup.

    A pending change-secret or push record must be treated as unverified. The
    remote credential may already have changed before the worker was
    terminated.
    """
    from accounts.models import (
        Account, AutomationExecution, ChangeSecretRecord, PushSecretRecord,
    )

    date_finished = timezone.now()
    account_ids = set()
    affected_account_ids = set()

    with tmp_to_root_org():
        with transaction.atomic():
            execution = AutomationExecution.objects.select_for_update().filter(
                id=execution_id,
                status__in=[Status.pending, Status.running],
            ).first()
            if not execution:
                return False

            change_records = ChangeSecretRecord.objects.filter(
                execution_id=execution_id,
                status=ChangeSecretRecordStatusChoice.pending.value,
            )
            account_ids.update(
                str(account_id)
                for account_id in change_records.values_list(
                    'account_id', flat=True
                )
                if account_id
            )
            affected_account_ids.update(account_ids)
            change_count = change_records.update(
                status=ChangeSecretRecordStatusChoice.unverified.value,
                error=reason,
                date_finished=date_finished,
            )

            push_records = PushSecretRecord.objects.filter(
                execution_id=execution_id,
                status=ChangeSecretRecordStatusChoice.pending.value,
            )
            push_account_ids = {
                str(account_id)
                for account_id in push_records.values_list(
                    'account_id', flat=True
                )
                if account_id
            }
            account_ids.update(push_account_ids)
            affected_account_ids.update(push_account_ids)
            push_count = push_records.update(
                status=ChangeSecretRecordStatusChoice.unverified.value,
                error=reason,
                date_finished=date_finished,
            )

            snapshot = execution.snapshot or {}
            verification_record_ids = list(
                (snapshot.get('recovery_record_map') or {}).values()
            )
            verification_count = 0
            if verification_record_ids:
                verification_count = ChangeSecretRecord.objects.filter(
                    id__in=verification_record_ids,
                    verification_status=(
                        ChangeSecretRecordStatusChoice.pending.value
                    ),
                ).update(
                    verification_status=(
                        ChangeSecretRecordStatusChoice.unverified.value
                    ),
                    verification_error=reason,
                    date_verified=date_finished,
                )

            retry_record_ids = [
                record_id
                for record_id in (
                    snapshot.get('record_map') or {}
                ).values()
                if record_id
            ]

            # A record retry deliberately reuses the original record, whose
            # execution FK still points at the original run. Include record_map
            # entries so a force-killed retry cannot leave that record pending.
            if retry_record_ids:
                retried_change_records = ChangeSecretRecord.objects.filter(
                    id__in=retry_record_ids,
                    status=ChangeSecretRecordStatusChoice.pending.value,
                ).exclude(execution_id=execution_id)
                retry_change_account_ids = {
                    str(account_id)
                    for account_id in retried_change_records.values_list(
                        'account_id', flat=True
                    )
                    if account_id
                }
                account_ids.update(retry_change_account_ids)
                affected_account_ids.update(retry_change_account_ids)
                change_count += retried_change_records.update(
                    status=ChangeSecretRecordStatusChoice.unverified.value,
                    error=reason,
                    date_finished=date_finished,
                )
                retried_push_records = PushSecretRecord.objects.filter(
                    id__in=retry_record_ids,
                    status=ChangeSecretRecordStatusChoice.pending.value,
                ).exclude(execution_id=execution_id)
                retry_push_account_ids = {
                    str(account_id)
                    for account_id in retried_push_records.values_list(
                        'account_id', flat=True
                    )
                    if account_id
                }
                account_ids.update(retry_push_account_ids)
                affected_account_ids.update(retry_push_account_ids)
                push_count += retried_push_records.update(
                    status=ChangeSecretRecordStatusChoice.unverified.value,
                    error=reason,
                    date_finished=date_finished,
                )

            account_ids.update(
                str(account_id)
                for account_id in snapshot.get('accounts', [])
                if account_id
            )
            Account.objects.filter(
                id__in=affected_account_ids
            ).update(
                change_secret_status=(
                    ChangeSecretRecordStatusChoice.unverified.value
                )
            )

            summary = dict(execution.summary or {})
            _increase_summary(
                summary, 'unverified_accounts', change_count + push_count
            )
            _increase_summary(
                summary, 'interrupted_accounts',
                change_count + push_count,
            )

            result = dict(execution.result or {})
            result['interruption'] = {
                'reason': str(reason),
                'date_finished': date_finished.isoformat(),
                'change_secret_records': change_count,
                'push_secret_records': push_count,
                'verification_records': verification_count,
            }

            execution.status = status
            execution.date_finished = date_finished
            if execution.date_start:
                execution.duration = round(
                    (date_finished - execution.date_start).total_seconds(), 2
                )
            execution.summary = summary
            execution.result = result
            execution.save(update_fields=[
                'status', 'date_finished', 'duration', 'summary', 'result',
            ])

    # Cache operations are intentionally outside the database transaction.
    # A cache outage must not roll back the recovered database state.
    from accounts.utils import account_secret_task_status
    from django.core.cache import cache
    for account_id in account_ids:
        try:
            metadata = account_secret_task_status.get(account_id) or {}
            owner = str(metadata.get('execution_id') or '')
            if not owner or owner == str(execution_id):
                account_secret_task_status.clear(account_id)
        except Exception:
            logger.exception(
                'Clear interrupted account task status failed: '
                'execution=%s account=%s',
                execution_id, account_id,
            )
        try:
            lock = cache.lock(
                f'account-change-secret:{account_id}',
                id=str(execution_id),
                auto_renewal=False,
            )
            if lock.get_owner_id() == str(execution_id):
                lock.release()
        except Exception:
            logger.exception(
                'Release interrupted account lock failed: '
                'execution=%s account=%s',
                execution_id, account_id,
            )
    try:
        _cleanup_interrupted_runtime(execution_id, snapshot)
    except Exception:
        logger.exception(
            'Clean interrupted automation runtime failed: execution=%s',
            execution_id,
        )

    logger.warning(
        'Interrupted account automation execution finalized: '
        'execution=%s status=%s change_secret=%s push_secret=%s',
        execution_id, status, change_count, push_count,
    )
    return True


def finalize_interrupted_executions_for_task(
        task_id, reason, status=Status.canceled
):
    """Finalize every active account execution owned by one Celery task."""
    from accounts.const import AutomationTypes
    from accounts.models import AutomationExecution

    task_id = str(task_id)
    with tmp_to_root_org():
        executions = list(
            AutomationExecution.objects.filter(
                status__in=[Status.pending, Status.running],
                type__in=list(AutomationTypes.values),
            ).only('id', 'snapshot')
        )

    finalized = 0
    for execution in executions:
        snapshot = execution.snapshot or {}
        owner_task_id = str(
            snapshot.get('celery_task_id') or execution.id
        )
        if owner_task_id != task_id:
            continue
        if finalize_interrupted_execution(
                execution.id, reason, status=status
        ):
            finalized += 1
    return finalized
