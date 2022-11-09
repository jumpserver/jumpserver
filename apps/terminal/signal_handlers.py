# -*- coding: utf-8 -*-
#

from django.db.models.signals import post_save
from django.dispatch import receiver

from orgs.utils import tmp_to_builtin_org
from .models import Applet, AppletHost


@receiver(post_save, sender=AppletHost)
def on_applet_host_create(sender, instance, created=False, **kwargs):
    if not created:
        return
    applets = Applet.objects.all()
    instance.applets.set(applets)
    with tmp_to_builtin_org(system=1):
        instance.generate_accounts()


@receiver(post_save, sender=Applet)
def on_applet_create(sender, instance, created=False, **kwargs):
    if not created:
        return
    hosts = AppletHost.objects.all()
    instance.hosts.set(hosts)
