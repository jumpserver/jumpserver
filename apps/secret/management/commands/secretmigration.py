from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.conf import settings

from secret.backends.endpoint import Secret
from assets.models import BaseUser
from assets.models import AuthBook
from applications.models import Account

STORAGE_TYPE = ('db', 'vault', 'pam')


class Command(BaseCommand):
    help = 'Secret key data migration'

    def add_arguments(self, parser):
        # parser.add_argument(
        #     'storage_type', type=str, choices=STORAGE_TYPE, help='Storage type'
        # )
        # parser.add_argument(
        #     'new_storage_type', type=str, choices=STORAGE_TYPE, help='New storage type'
        # )
        pass

    def handle(self, *args, **options):
        # storage_type = options['storage_type']
        # if storage_type != 'db':
        #     raise CommandError('Currently, only starting migration from the database is supported')
        # new_storage_type = options['new_storage_type']
        # if new_storage_type == 'db':
        #     raise CommandError('No migration required')
        fields = BaseUser.SECRET_FIELD
        backend = settings.SECRET_STORAGE_BACKEND
        for model in apps.get_models():
            if Secret.is_allow(model):
                for instance in model.objects.all():
                    if issubclass(model, (AuthBook, Account)):
                        instance.load_auth()
                    secret_data = {field: getattr(instance, field) for field in fields}
                    if any(secret_data.values()):
                        Secret(instance, backend).create_secret(secret_data)
                model.objects.update(**{i: None for i in fields})
        self.stdout.write(self.style.SUCCESS('Secret migration succeeded'))
