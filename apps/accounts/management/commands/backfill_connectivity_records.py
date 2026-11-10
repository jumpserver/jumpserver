from uuid import UUID

from django.core.management.base import BaseCommand

from accounts.automations.connectivity import backfill_connectivity_records
from accounts.models import ConnectivityRecord
from assets.models import AutomationExecution


class Command(BaseCommand):
    help = 'Backfill connectivity records from completed executions and available legacy logs.'

    def add_arguments(self, parser):
        parser.add_argument('--database', default='default')
        parser.add_argument('--execution-id', type=UUID)

    def handle(self, *args, **options):
        using = options['database']
        executions = AutomationExecution._base_manager.using(using).all()
        if options['execution_id']:
            executions = executions.filter(id=options['execution_id'])
        count = backfill_connectivity_records(executions, ConnectivityRecord, using)
        self.stdout.write(self.style.SUCCESS(f'Backfilled {count} connectivity records.'))
