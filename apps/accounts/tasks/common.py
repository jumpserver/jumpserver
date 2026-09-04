import uuid

from celery import shared_task
from assets.tasks.common import generate_automation_execution_data
from common.const.choices import Trigger
from orgs.utils import tmp_to_org


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


@shared_task(queue='ansible')
def execute_credential_change(execution_id, org_id):
    from accounts.models import AutomationExecution, ApplicationCredential
    from django.utils import timezone
    with tmp_to_org(org_id):
        execution = AutomationExecution.objects.get(id=execution_id)
        try:
            execution.start()
        finally:
            execution.refresh_from_db()
            if execution.is_finished and not execution.is_success:
                credential = ApplicationCredential.objects.filter(change_execution_id=execution_id).first()
                if credential:
                    credential.rotation_records.filter(status='running').update(
                        status='failed', date_finished=timezone.now(),
                        comment='Secret change failed or needs verification. Check the execution record.',
                    )
