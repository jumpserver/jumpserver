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
