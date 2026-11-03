"""Prepare usable workflows on upgrade without replacing administrator choices."""
import logging

from django.db import transaction

from orgs.models import Organization
from orgs.utils import tmp_to_root_org
from rbac.builtin import BuiltinRole
from tickets.management.commands.migrate_ticket_workflows import import_flow
from tickets.models import TicketFlow, Workflow
from tickets.plugins import ticket_plugins
from .errors import WorkflowConfigurationError
from .publication import publish_workflow

logger = logging.getLogger(__name__)


@transaction.atomic
def create_default_workflow(org_id, plugin):
    # Existing drafts and disabled definitions are deliberate administrator choices.
    scopes = [str(org_id), Organization.ROOT_ID]
    if (Workflow.objects.filter(org_id__in=scopes, type=plugin.type, is_system=False).exists()
            or TicketFlow.objects.filter(org_id__in=scopes, type=plugin.type).exists()):
        return
    workflow = Workflow.objects.create(
        org_id=str(org_id), type=plugin.type, name=str(plugin.label),
        enabled=True, created_by='System',
    )
    publish_workflow(workflow, {
        'nodes': [
            {'id': 'start', 'type': 'start'},
            {'id': 'approval', 'type': 'approval', 'name': 'Approval', 'config': {
                'approvers': {'type': 'role', 'value': [BuiltinRole.system_admin.id]},
                'strategy': 'any',
            }},
            {'id': 'end', 'type': 'end'},
        ],
        'edges': [['start', 'approval'], ['approval', 'end']],
    }, expected_version=0)


def ensure_default_workflows(org_ids=None):
    with tmp_to_root_org():
        for plugin in ticket_plugins.all(visible=True):
            existing = Workflow.objects.filter(type=plugin.type, is_system=False).exists()
            legacy = TicketFlow.objects.filter(type=plugin.type).exists()
            if org_ids is None and not existing and not legacy:
                # Fresh types inherit a single global definition, like the old default.
                create_default_workflow(Organization.ROOT_ID, plugin)
                continue
            scopes = org_ids if org_ids is not None else list(Organization.objects.exclude(
                pk__in=[Organization.ROOT_ID, Organization.SYSTEM_ID],
            ).values_list('id', flat=True))
            for org_id in scopes:
                create_default_workflow(org_id, plugin)


def initialize_workflows():
    with tmp_to_root_org():
        for flow in TicketFlow.objects.all().order_by('id').iterator():
            try:
                workflow = import_flow(flow, enabled=True, preserve_roles=True)
                if not workflow.enabled and workflow.migration_notes.get('requires_review'):
                    logger.warning('Legacy workflow %s requires review before enabling.', flow.pk)
            except WorkflowConfigurationError as exc:
                # Never bypass an invalid custom approval rule with a new default.
                Workflow.objects.get_or_create(
                    org_id=flow.org_id, type=flow.type, name=flow.name or flow.get_type_display(),
                    defaults={'legacy_flow_id': flow.pk, 'created_by': 'Legacy workflow import',
                              'migration_notes': {'requires_review': True, 'error': str(exc.detail)}},
                )
                logger.warning('Could not initialize legacy workflow %s: %s', flow.pk, exc.detail)
        ensure_default_workflows()
