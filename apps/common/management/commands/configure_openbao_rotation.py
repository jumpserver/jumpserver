import getpass
import json
import sys

from django.core.management.base import BaseCommand, CommandError

from accounts.tasks.openbao import configure_approle


class Command(BaseCommand):
    help = 'Save encrypted AppRole credentials for automatic OpenBao vault token rotation.'

    def add_arguments(self, parser):
        parser.add_argument('--auth-mount', default='approle')
        parser.add_argument('--stdin', action='store_true', help='Read role_id and secret_id as JSON.')

    def handle(self, *args, **options):
        if options['stdin']:
            try:
                credentials = json.load(sys.stdin)
                role_id, secret_id = credentials['role_id'], credentials['secret_id']
            except (ValueError, TypeError, KeyError):
                raise CommandError('Expected JSON with role_id and secret_id.') from None
        elif sys.stdin.isatty():
            role_id = input('AppRole role ID: ')
            secret_id = getpass.getpass('AppRole secret ID: ')
        else:
            raise CommandError('Use --stdin to supply credentials without a terminal.')

        try:
            configure_approle(options['auth_mount'], role_id, secret_id)
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(self.style.SUCCESS('OpenBao rotation AppRole credentials saved.'))
