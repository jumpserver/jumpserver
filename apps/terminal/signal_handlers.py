# -*- coding: utf-8 -*-
#

from django.db.models.signals import post_save, post_delete
from django.db.utils import ProgrammingError
from django.dispatch import receiver

from common.signals import django_ready
from common.utils import get_logger
from orgs.utils import tmp_to_builtin_org
from assets.models import Asset
from .utils import db_port_manager, DBPortManager
from .models import Applet, AppletHost

db_port_manager: DBPortManager


logger = get_logger(__file__)


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


@receiver(django_ready)
def init_db_port_mapper(sender, **kwargs):
    logger.info('Init db port mapper')
    try:
        db_port_manager.init()
    except (ProgrammingError,) as e:
        pass


@receiver(post_save, sender=Asset)
def on_db_app_created(sender, instance: Asset, created, **kwargs):
    if not instance.category != 'database':
        return
    if not created:
        return
    db_port_manager.add(instance)


@receiver(post_delete, sender=Asset)
def on_db_app_delete(sender, instance, **kwargs):
    if not instance.category != 'database':
        return
    db_port_manager.pop(instance)
