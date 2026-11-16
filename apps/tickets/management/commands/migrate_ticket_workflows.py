"""One-off, idempotent import of legacy definitions, never of active approvals."""
from importlib import import_module

from django.apps import apps
from django.core.exceptions import FieldError, ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import router, transaction

from orgs.utils import tmp_to_root_org
from tickets.models import TicketFlow, Workflow
from tickets.workflow.definition import validate_definition
from tickets.workflow.errors import WorkflowConfigurationError
from tickets.workflow.publication import publish_workflow


def convert_flow(flow):
    converter = import_module('tickets.migrations.0010_ticket_workflow_refactor').convert_flow
    try:
        definition, notes = converter(apps, router.db_for_read(TicketFlow, instance=flow), flow)
    except (ValueError, TypeError, AttributeError, FieldError, ValidationError) as exc:
        raise WorkflowConfigurationError(str(exc)) from exc
    return validate_definition(definition), notes


@transaction.atomic
def import_flow(flow):
    flow = TicketFlow.objects.select_for_update().get(pk=flow.pk)
    existing = Workflow.objects.filter(legacy_flow_id=flow.pk).first()
    if existing:
        return existing
    definition, notes = convert_flow(flow)
    name = flow.name or flow.get_type_display()
    if Workflow.objects.filter(org_id=flow.org_id, type=flow.type, name=name).exists():
        name = f'{name[:90]} ({flow.pk})'
    workflow = Workflow.objects.create(
        name=name, type=flow.type, org_id=flow.org_id,
        legacy_flow_id=flow.pk, migration_notes=notes, enabled=True,
        created_by='Legacy workflow import',
    )
    publish_workflow(workflow, definition, expected_version=0)
    return workflow


class Command(BaseCommand):
    help = ('Preview legacy workflow imports. Use --apply to publish and enable workflows '
            'with their original selectors.')

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
                        definition, _ = convert_flow(flow)
                        if options['apply']:
                            import_flow(flow)
                        imported += 1
                        mode = 'IMPORTED (enabled)' if options['apply'] else 'WOULD IMPORT'
                        approvals = sum(node['type'] == 'approval' for node in definition['nodes'])
                        self.stdout.write(
                            f'{mode} {flow.pk}: {approvals} approval nodes; '
                            'original selectors preserved'
                        )
                except WorkflowConfigurationError as exc:
                    failed += 1
                    self.stderr.write(f'FAILED {flow_id}: {exc.detail}')
        self.stdout.write(f'{imported} definitions, {skipped} already imported, {failed} failed. Existing tickets were not changed.')
        if failed:
            raise CommandError('Some definitions could not be imported; correct their approval rules and run again.')
