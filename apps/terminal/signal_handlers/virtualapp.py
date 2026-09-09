import shutil

from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from common.decorators import on_transaction_commit
from common.utils import get_logger
from terminal.utils.virtualapp import archive_root
from ..models import AppProvider, VirtualApp

logger = get_logger(__name__)


@receiver(post_save, sender=AppProvider)
@on_transaction_commit
def on_virtual_host_create(sender, instance, created=False, **kwargs):
    if not created:
        return
    apps = VirtualApp.objects.all()
    instance.apps.set(apps)


@receiver(post_save, sender=VirtualApp)
def on_virtual_app_create(sender, instance, created=False, **kwargs):
    if not created:
        return
    providers = AppProvider.objects.all()
    if len(providers) == 0:
        return
    instance.providers.set(providers)


@receiver(post_delete, sender=VirtualApp)
def on_virtual_app_delete(sender, instance, **kwargs):
    path = archive_root(instance)

    def cleanup():
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass
        except OSError:
            logger.exception('Failed to remove offline images for virtual app %s', path.name)

    transaction.on_commit(cleanup)
