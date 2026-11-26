from django.db.models import CharField, F, Q, Value

from acls.models import CommandFilterACL, LoginACL, LoginAssetACL
from orgs.models import Organization
from orgs.utils import current_org, tmp_to_root_org
from tickets.models import Ticket, Workflow


def combined_workflow_ids(workflow, version_ids):
    if workflow.type != 'login_asset_confirm' or not version_ids:
        return []
    # Combined ACL workflows keep their source version IDs in JSON.
    with tmp_to_root_org():
        sources = Workflow.objects.filter(
            is_system=True, type=workflow.type, migration_notes__has_key='source_versions',
        ).values_list('pk', 'migration_notes__source_versions')
        return [pk for pk, ids in sources.iterator() if not version_ids.isdisjoint(ids)]


def reference_rows(queryset, label, org, *, ticket=False):
    return queryset.order_by().annotate(
        kind=Value(queryset.model._meta.model_name), record_name=F(label), record_org=org,
        record_number=F('serial_num') if ticket else Value('', output_field=CharField()),
        ticket_type=F('type') if ticket else Value('', output_field=CharField()),
    ).values('kind', 'record_name', 'id', 'record_org', 'record_number', 'ticket_type')


def visible_workflow_references(workflow, user):
    version_ids = {str(pk) for pk in workflow.versions.values_list('pk', flat=True)}
    combined = combined_workflow_ids(workflow, version_ids)
    flows = [workflow.pk, *combined]
    # System-generated combinations have no designer page. Show their tickets as well.
    rows = [reference_rows(Workflow.objects.filter(pk__in=combined), 'name', F('org_id'))]
    for model in (LoginACL, LoginAssetACL, CommandFilterACL):
        if user.has_perm(f'acls.view_{model._meta.model_name}'):
            org = Value(Organization.ROOT_ID) if model is LoginACL else F('org_id')
            rows.append(reference_rows(model.objects.filter(workflow=workflow), 'name', org))

    can_audit = user.has_perm('audits.view_ticketaudit')
    if can_audit or user.has_perm('tickets.view_ticket'):
        tickets = Ticket.get_viewable_tickets(user, can_audit).filter(
            Q(workflow_id__in=flows) | Q(workflow_instance__version__workflow_id__in=flows)
        )
        if not current_org.is_root():
            tickets = tickets.filter(org_id=current_org.id)
        rows.append(reference_rows(tickets, 'title', F('org_id'), ticket=True))
    return rows[0].union(*rows[1:], all=True).order_by('kind', 'record_name', 'id')
