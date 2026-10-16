from django.core.management.base import BaseCommand, CommandError
from orgs.utils import tmp_to_root_org
from tickets.models import Ticket
from tickets.workflow.migration import import_ticket


class Command(BaseCommand):
    help = 'Preview or import historical and open tickets. Never replays business effects. Invalid open tickets become errors.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--org-id')
        parser.add_argument('--ticket-id')

    def handle(self, *args, **options):
        failed = 0
        with tmp_to_root_org():
            qs = Ticket.objects.filter(workflow_instance__isnull=True).order_by('date_created', 'id')
            if options['org_id']:
                qs = qs.filter(org_id=options['org_id'])
            if options['ticket_id']:
                qs = qs.filter(pk=options['ticket_id'])
            for pk in qs.values_list('pk', flat=True).iterator():
                try:
                    result, warnings = import_ticket(pk, apply=options['apply'])
                    self.stdout.write(f'{result} {pk}')
                    for warning in warnings:
                        self.stdout.write(f'  WARNING: {warning}')
                except Exception as exc:
                    failed += 1
                    self.stderr.write(f'FAILED {pk}: {exc}')
        if failed:
            raise CommandError(f'{failed} imports failed. Each ticket is atomic; correct the errors and rerun.')
