from celery import shared_task
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_root_org, tmp_to_org
from tickets.models import WorkflowInstance
from tickets.workflow.engine import WorkflowEngine


@shared_task(
    verbose_name=_('Expire overdue ticket approvals'),
    description=_('Check approval deadlines every minute and apply the configured timeout action.'),
)
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


@shared_task(
    bind=True, queue='ansible', verbose_name=_('Execute ticket password change'),
    description=_('Change account passwords according to the approved ticket resources.'),
)
def execute_ticket_change_secret(self, execution_id):
    from tickets.plugins.change_secret.execution import execute
    execute(execution_id, self.request.id, self.request.hostname)


@shared_task(
    verbose_name=_('Dispatch ticket password changes'),
    description=_('Dispatch pending password change executions every minute.'),
)
@register_as_period_task(interval=60)
def dispatch_ticket_change_secrets():
    from tickets.plugins.change_secret.execution import pending_executions, dispatch_execution
    with tmp_to_root_org():
        ids = list(pending_executions().order_by('date_created').values_list('id', flat=True)[:100])
    for execution_id in ids:
        dispatch_execution(execution_id)
    return len(ids)


@shared_task(
    queue='ansible', soft_time_limit=900, time_limit=960,
    verbose_name=_('Execute ticket file transfer'),
    description=_('Transfer files according to the approved ticket resources.'),
)
def execute_ticket_file_transfer(ticket_id):
    from tickets.plugins.file_transfer.execution import execute
    execute(ticket_id)


@shared_task(
    verbose_name=_('Maintain ticket file transfers'),
    description=_('Check queued and running file transfers every five minutes and handle expired transfers.'),
)
@register_as_period_task(interval=300)
def maintain_ticket_file_transfers():
    from tickets.plugins.file_transfer.execution import maintain
    return maintain()


@shared_task(
    verbose_name=_('Clean ticket transfer files'),
    description=_('Clean expired temporary files from ticket transfers every hour.'),
)
@register_as_period_task(interval=3600)
def cleanup_ticket_transfer_files():
    from tickets.plugins.file_transfer.execution import cleanup
    return cleanup()
