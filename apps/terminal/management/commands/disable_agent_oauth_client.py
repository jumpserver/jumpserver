from django.core.management.base import BaseCommand, CommandError

from terminal.models import AgentApplication


class Command(BaseCommand):
    help = 'Disable an Agent OAuth client and revoke its execution authorization.'

    def add_arguments(self, parser):
        parser.add_argument('--client-id', required=True)

    def handle(self, *args, **options):
        updated = AgentApplication.objects.filter(application__client_id=options['client_id']).update(is_active=False)
        if not updated:
            raise CommandError('Unknown Agent client')
        self.stdout.write('Agent client disabled; execution authorization is revoked.')
