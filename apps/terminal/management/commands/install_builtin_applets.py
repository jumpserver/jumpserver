from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Install builtin applets'

    def handle(self, *args, **options):
        from terminal.applets import install_or_update_builtin_applets
        install_or_update_builtin_applets()
