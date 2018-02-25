# -*- coding: utf-8 -*-
#

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from common.utils import get_logger
from .models import Asset, SystemUser, Node
from .tasks import update_assets_hardware_info_util, \
    test_asset_connectability_util, push_system_user_to_node, \
    push_node_system_users_to_asset


logger = get_logger(__file__)


def update_asset_hardware_info_on_created(asset):
    logger.debug("Update asset `{}` hardware info".format(asset))
    update_assets_hardware_info_util.delay([asset])


def test_asset_conn_on_created(asset):
    logger.debug("Test asset `{}` connectability".format(asset))
    test_asset_connectability_util.delay(asset)


def set_asset_root_node(asset):
    logger.debug("Set asset default node: {}".format(Node.root()))
    asset.nodes.add(Node.root())


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
def on_asset_created_or_update(sender, instance=None, created=False, **kwargs):
    set_asset_root_node(instance)
    if created:
        logger.info("Asset `{}` create signal received".format(instance))
        update_asset_hardware_info_on_created(instance)
        test_asset_conn_on_created(instance)


@receiver(post_save, sender=SystemUser, dispatch_uid="my_unique_identifier")
def on_system_user_update(sender, instance=None, created=True, **kwargs):
    if instance and not created:
        for node in instance.nodes.all():
            push_system_user_to_node(instance, node)


@receiver(m2m_changed, sender=SystemUser.nodes.through)
def on_system_user_node_change(sender, instance=None, **kwargs):
    if instance and kwargs["action"] == "post_add":
        for pk in kwargs['pk_set']:
            node = kwargs['model'].objects.get(pk=pk)
            push_system_user_to_node(instance, node)


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_asset_node_changed(sender, instance=None, **kwargs):
    if isinstance(instance, Asset) and kwargs['action'] == 'post_add':
        logger.debug("Asset node change signal received")
        for pk in kwargs['pk_set']:
            node = kwargs['model'].objects.get(pk=pk)
            push_node_system_users_to_asset(node, [instance])


@receiver(m2m_changed, sender=Asset.nodes.through)
def on_node_assets_changed(sender, instance=None, **kwargs):
    if isinstance(instance, Node) and kwargs['action'] == 'post_add':
        logger.debug("Node assets change signal received")
        assets = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
        push_node_system_users_to_asset(instance, assets)

