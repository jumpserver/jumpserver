import uuid

from celery import shared_task
from assets.tasks.common import generate_automation_execution_data
from common.const.choices import Trigger
from orgs.utils import tmp_to_org


@shared_task(queue='ansible', soft_time_limit=600, time_limit=660)
def execute_credential_precheck(execution_id, org_id):
    from accounts.credential_rotation.preflight import run
    with tmp_to_org(org_id):
        run(execution_id)


def quickstart_automation_by_snapshot(task_name, tp, task_snapshot=None):
    from accounts.models import AutomationExecution
    data = generate_automation_execution_data(task_name, tp, task_snapshot)

    pk = data['id']
    if AutomationExecution.objects.filter(id=pk).exists():
        data['id'] = str(uuid.uuid4())

    execution = AutomationExecution.objects.create(
        type=tp, trigger=Trigger.manual, **data
    )
    execution.start()
    return execution


@shared_task(queue='ansible')
def execute_credential_change(execution_id, org_id):
    from accounts.models import AutomationExecution, Account, ChangeSecretRecord
    from accounts.credential_rotation.execution import locked_rotation, reconcile
    from django.db import transaction
    from django.utils import timezone
    from celery import current_task
    from common.const import Status
    with tmp_to_org(org_id):
        with transaction.atomic():
            initial = AutomationExecution.objects.get(id=execution_id)
            credential, rotation = locked_rotation(initial.snapshot['credential_rotation_id'])
            execution = AutomationExecution.objects.select_for_update().get(id=execution_id)
            if execution.status != Status.pending:
                return
            if rotation.change_execution_id != execution.id or credential.change_execution_id != execution.id:
                return
            primary = Account.objects.get(id=credential.primary_account_id)
            if primary.version != execution.snapshot['expected_account_version']:
                execution.status = Status.failed
                execution.date_finished = timezone.now()
                execution.save(update_fields=['status', 'date_finished'])
                transaction.on_commit(lambda: reconcile(execution_id))
                return
            execution.status = Status.running
            execution.date_start = timezone.now()
            execution.snapshot.update(
                celery_task_id=str(execution.id),
                celery_worker_hostname=current_task.request.hostname,
            )
            execution.save(update_fields=['status', 'date_start', 'snapshot'])
        try:
            execution.start()
        finally:
            execution.refresh_from_db()
            if not execution.is_finished:
                from accounts.automations.recovery import finalize_interrupted_execution
                finalize_interrupted_execution(execution.id, 'Rotation execution interrupted.')
            if not ChangeSecretRecord.objects.filter(execution_id=execution.id).exists():
                execution.refresh_from_db()
                execution.summary['rotation_no_remote_change'] = True
                execution.save(update_fields=['summary'])
            reconcile(execution_id)
