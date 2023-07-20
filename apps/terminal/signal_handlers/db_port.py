from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from assets.models import Asset, Database
from common.decorators import on_transaction_commit
from common.signals import django_ready
from common.utils import get_logger
from ..utils import db_port_manager

logger = get_logger(__file__)


@receiver(django_ready)
def check_db_port_mapper(sender, **kwargs):
    logger.info('Check oracle ports (MAGNUS_ORACLE_PORTS)')
    try:
        db_port_manager.check()
    except Exception as e:
        logger.error(e)


@receiver(post_save, sender=Database)
def on_db_created(sender, instance: Database, created, **kwargs):
    if instance.type != 'oracle':
        return
    if not created:
        return
    logger.info("Oracle create signal recv: {} {}".format(instance, instance.type))
    db_port_manager.check()


@receiver(post_delete, sender=Asset)
@on_transaction_commit
def on_db_delete(sender, instance, **kwargs):
    if instance.type != 'oracle':
        return
    logger.info("Oracle delete signal recv: {}".format(instance))
    db_port_manager.check()
