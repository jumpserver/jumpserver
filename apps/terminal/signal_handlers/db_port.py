from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from assets.models import Asset
from common.signals import django_ready
from common.utils import get_logger
from ..utils import db_port_manager

logger = get_logger(__file__)


@receiver(django_ready)
def check_db_port_mapper(sender, **kwargs):
    logger.info('Init db port mapper')
    try:
        db_port_manager.check()
    except Exception as e:
        pass


@receiver(post_save, sender=Asset)
def on_db_created(sender, instance: Asset, created, **kwargs):
    print("Asset create: ", instance)
    if not instance.category != 'database':
        return
    if not created:
        return
    db_port_manager.add(instance)


@receiver(post_delete, sender=Asset)
def on_db_delete(sender, instance, **kwargs):
    print("Asset delete: ", instance)
    if not instance.category != 'database':
        return
    db_port_manager.pop(instance)
