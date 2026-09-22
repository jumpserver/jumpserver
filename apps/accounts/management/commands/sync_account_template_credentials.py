from django.core.management.base import BaseCommand

from accounts.const import Source
from accounts.models import Account
from accounts.tasks.template import template_sync_related_accounts
from orgs.utils import tmp_to_root_org


class Command(BaseCommand):
    help = 'Initialize stored credential copies for existing template-following accounts.'

    def handle(self, *args, **options):
        with tmp_to_root_org():
            template_ids = list(Account.objects.filter(
                source=Source.TEMPLATE, follow_template=True,
            ).exclude(source_id__isnull=True).exclude(source_id='').order_by().values_list(
                'source_id', flat=True,
            ).distinct())
        for template_id in template_ids:
            template_sync_related_accounts.delay(template_id, initialize=True)
        self.stdout.write(f'Scheduled credential initialization for {len(template_ids)} templates.')
