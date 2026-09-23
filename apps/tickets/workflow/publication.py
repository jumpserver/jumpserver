from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from tickets.models import Workflow, WorkflowVersion, WorkflowNode, WorkflowEdge
from .definition import validate_definition
from .errors import WorkflowConflict


@transaction.atomic
def publish_workflow(workflow, definition, *, actor=None, expected_version=None):
    definition = validate_definition(definition)
    workflow = Workflow.objects.select_for_update().get(pk=workflow.pk)
    current = workflow.active_version.number if workflow.active_version_id else 0
    if expected_version is not None and expected_version != current:
        raise WorkflowConflict('A newer version was published. Reload before publishing.')
    number = (workflow.versions.aggregate(latest=Max('number'))['latest'] or 0) + 1
    version = WorkflowVersion.objects.create(
        workflow=workflow, number=number, created_by=str(actor)[:128] if actor else '',
    )
    nodes = {}
    for item in definition['nodes']:
        nodes[item['id']] = WorkflowNode.objects.create(
            version=version, key=item['id'], type=item['type'], name=item['name'], config=item['config'],
            position_x=item['position']['x'], position_y=item['position']['y'],
        )
    WorkflowEdge.objects.bulk_create([
        WorkflowEdge(version=version, source=nodes[edge['source']], target=nodes[edge['target']],
                     condition=edge['condition'], priority=edge['priority'])
        for edge in definition['edges']
    ])
    version.published_at = timezone.now()
    version.save(update_fields=['published_at'])
    workflow.active_version = version
    workflow.save(update_fields=['active_version', 'date_updated'])
    return version
