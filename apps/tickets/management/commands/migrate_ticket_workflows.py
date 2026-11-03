"""One-off, idempotent import of legacy definitions, never of active approvals."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from orgs.utils import tmp_to_root_org
from tickets.models import TicketFlow, Workflow
from tickets.workflow.definition import validate_definition
from tickets.workflow.errors import WorkflowConfigurationError
from tickets.workflow.publication import publish_workflow


def convert_flow(flow, *, preserve_roles=False):
    nodes = [{'id': 'start', 'type': 'start'}]
    edges, previous, notes = [], 'start', []
    selectors_preserved = preserve_roles
    cc_user_ids = [str(pk) for pk in flow.cc_users.values_list('pk', flat=True)]
    if cc_user_ids:
        nodes.append({'id': 'cc_legacy', 'type': 'cc', 'name': 'CC', 'config': {'users': cc_user_ids}})
        edges.append([previous, 'cc_legacy'])
        previous = 'cc_legacy'
    rules = list(flow.rules.order_by('level', 'id'))
    if not rules:
        raise WorkflowConfigurationError('The legacy flow has no approval rules.')
    for index, rule in enumerate(rules, 1):
        selector = rule.users.value or {}
        attrs = selector.get('attrs', []) if selector.get('type') == 'attrs' else []
        role_filter = attrs[0] if len(attrs) == 1 else {}
        if (preserve_roles and isinstance(role_filter, dict)
                and role_filter.get('name') in ('system_roles', 'org_roles')
                and role_filter.get('match') == 'm2m' and role_filter.get('value')):
            approvers = {'type': 'role', 'value': role_filter['value']}
            count = None
        else:
            if selector.get('type') != 'ids':
                selectors_preserved = False
            users = list(rule.get_assignees(org_id=flow.org_id).order_by('id'))
            if not users:
                raise WorkflowConfigurationError(f'No approvers matched legacy level {rule.level}.')
            approvers = {'type': 'user', 'value': [str(user.pk) for user in users]}
            count = len(users)
        key = f'approval_{index}'
        nodes.append({'id': key, 'type': 'approval', 'name': f'Approval {index}', 'config': {
            'approvers': approvers, 'strategy': 'any',
        }})
        edges.append([previous, key])
        notes.append({'level': rule.level, 'legacy_selector': selector, 'resolved_user_count': count})
        previous = key
    nodes.append({'id': 'end', 'type': 'end'})
    edges.append([previous, 'end'])
    return validate_definition({'nodes': nodes, 'edges': edges}), {
        'rules': notes, 'cc_user_ids': cc_user_ids,
        'requires_review': not selectors_preserved,
        'notice': 'Legacy selectors were resolved to fixed users. Review organization scope, applicant exclusion and CC before enabling.',
    }


@transaction.atomic
def import_flow(flow, *, enabled=False, preserve_roles=False):
    flow = TicketFlow.objects.select_for_update().get(pk=flow.pk)
    existing = Workflow.objects.filter(legacy_flow_id=flow.pk).first()
    if existing:
        return existing
    definition, notes = convert_flow(flow, preserve_roles=preserve_roles)
    name = flow.name or flow.get_type_display()
    if Workflow.objects.filter(org_id=flow.org_id, type=flow.type, name=name).exists():
        name = f'{name[:90]} ({flow.pk})'
    if enabled:
        enabled = not notes['requires_review']
        notes['notice'] = (
            'Imported during upgrade; explicit users and single-role selectors are preserved.' if enabled else
            'Complex legacy selectors were resolved to fixed users. Review before enabling.'
        )
    workflow = Workflow.objects.create(
        name=name, type=flow.type, org_id=flow.org_id,
        legacy_flow_id=flow.pk, migration_notes=notes, enabled=enabled,
        created_by='Legacy workflow import',
    )
    publish_workflow(workflow, definition, expected_version=0)
    return workflow


class Command(BaseCommand):
    help = 'Preview legacy workflow imports. Use --apply to create disabled, published workflows for review.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--org-id')
        parser.add_argument('--flow-id')

    def handle(self, *args, **options):
        imported, skipped, failed = 0, 0, 0
        with tmp_to_root_org():
            flows = TicketFlow.objects.all().order_by('id')
            if options['org_id']:
                flows = flows.filter(org_id=options['org_id'])
            if options['flow_id']:
                flows = flows.filter(pk=options['flow_id'])
            for flow_id in flows.values_list('pk', flat=True).iterator():
                try:
                    with transaction.atomic():
                        flow = TicketFlow.objects.select_for_update().get(pk=flow_id)
                        if Workflow.objects.filter(legacy_flow_id=flow.pk).exists():
                            skipped += 1
                            self.stdout.write(f'SKIP {flow.pk}: already imported')
                            continue
                        definition, notes = convert_flow(flow)
                        if options['apply']:
                            import_flow(flow)
                        imported += 1
                        mode = 'IMPORTED (disabled)' if options['apply'] else 'WOULD IMPORT'
                        approvals = sum(node['type'] == 'approval' for node in definition['nodes'])
                        self.stdout.write(f'{mode} {flow.pk}: {approvals} approval nodes; review fixed user selectors and CC')
                except WorkflowConfigurationError as exc:
                    failed += 1
                    self.stderr.write(f'FAILED {flow_id}: {exc.detail}')
        self.stdout.write(f'{imported} definitions, {skipped} already imported, {failed} failed. Existing tickets were not changed.')
        if failed:
            raise CommandError('Some definitions could not be imported; correct their approval rules and run again.')
