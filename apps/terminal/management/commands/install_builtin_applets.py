from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Install builtin applets'

    def handle(self, *args, **options):
        from terminal.applets import install_or_update_builtin_applets
        from terminal.models import Applet

        install_or_update_builtin_applets()
        Applet.objects.filter(
            builtin=True, name__in=('chrome', 'dbeaver'), publications__isnull=True,
        ).update(is_active=False)
