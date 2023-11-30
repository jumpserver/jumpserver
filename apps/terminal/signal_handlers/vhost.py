from django.db.models.signals import post_save
from django.dispatch import receiver

from common.decorators import on_transaction_commit
from ..models import VirtualHost, VirtualApp


@receiver(post_save, sender=VirtualHost)
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
    hosts = VirtualHost.objects.all()
    if len(hosts) == 0:
        return
    instance.hosts.set(hosts)
