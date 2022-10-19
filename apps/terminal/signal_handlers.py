# -*- coding: utf-8 -*-
#
from django.db.models.signals import post_save, post_delete
from django.db.utils import ProgrammingError

from common.signals import django_ready
from django.dispatch import receiver
from common.utils import get_logger
from .models import Application
from .utils import db_port_manager, DBPortManager

db_port_manager: DBPortManager


logger = get_logger(__file__)


@receiver(django_ready)
def init_db_port_mapper(sender, **kwargs):
    logger.info('Init db port mapper')
    try:
        db_port_manager.init()
    except (ProgrammingError,) as e:
        pass


@receiver(post_save, sender=Application)
def on_db_app_created(sender, instance: Application, created, **kwargs):
    if not instance.category_db:
        return
    if not created:
        return
    db_port_manager.add(instance)


@receiver(post_delete, sender=Application)
def on_db_app_delete(sender, instance, **kwargs):
    if not instance.category_db:
        return
    db_port_manager.pop(instance)
