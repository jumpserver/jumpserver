from django.db.models.signals import post_save
from django.dispatch import receiver

from common.decorators import on_transaction_commit
from ..models import AppProvider, VirtualApp


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
