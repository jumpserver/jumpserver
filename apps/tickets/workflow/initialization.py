"""Prepare usable workflows for new organizations without replacing administrator choices."""

from django.db import transaction

from orgs.models import Organization
from orgs.utils import tmp_to_root_org
from rbac.builtin import BuiltinRole
from tickets.models import TicketFlow, Workflow
from tickets.plugins import ticket_plugins
from .publication import publish_workflow


@transaction.atomic
def create_default_workflow(org_id, plugin):
    if plugin.type == 'login_confirm':
        org_id = Organization.ROOT_ID
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
