from celery import shared_task
from django.utils import timezone

from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_root_org, tmp_to_org
from tickets.models import WorkflowInstance
from tickets.workflow.engine import WorkflowEngine


@shared_task
@register_as_period_task(interval=60)
def expire_workflow_approvals():
    with tmp_to_root_org():
        due = list(WorkflowInstance.objects.filter(
            state='running', node_instances__state='running',
            node_instances__deadline__lte=timezone.now(),
        ).distinct().order_by('node_instances__deadline').values_list('id', 'org_id')[:500])
    engine = WorkflowEngine()
    for pk, org_id in due:
        with tmp_to_org(org_id):
            engine.expire(WorkflowInstance(pk=pk))
    return len(due)


@shared_task(bind=True, queue='ansible')
def execute_ticket_change_secret(self, execution_id):
    from tickets.plugins.change_secret.execution import execute
    execute(execution_id, self.request.id, self.request.hostname)


@shared_task
@register_as_period_task(interval=60)
def dispatch_ticket_change_secrets():
    from tickets.plugins.change_secret.execution import pending_executions, dispatch_execution
    with tmp_to_root_org():
        ids = list(pending_executions().order_by('date_created').values_list('id', flat=True)[:100])
    for execution_id in ids:
        dispatch_execution(execution_id)
    return len(ids)


@shared_task(queue='ansible', soft_time_limit=900, time_limit=960)
def execute_ticket_file_transfer(ticket_id):
    from tickets.plugins.file_transfer.execution import execute
    execute(ticket_id)


@shared_task
@register_as_period_task(interval=60)
def maintain_ticket_file_transfers():
    from tickets.plugins.file_transfer.execution import maintain
    return maintain()
