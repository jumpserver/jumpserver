# -*- coding: utf-8 -*-
#


from django.db.models.signals import post_save, post_init, m2m_changed, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext as _

from common.utils import get_logger
from .models import Asset, SystemUser, Cluster
from .tasks import update_assets_hardware_info_util, \
    test_asset_connectability_util, \
    push_system_user_util


logger = get_logger(__file__)


def update_asset_hardware_info_on_created(asset):
    logger.debug("Update asset `{}` hardware info".format(asset))
    update_assets_hardware_info_util.delay([asset])


def test_asset_conn_on_created(asset):
    logger.debug("Test asset `{}` connectability".format(asset))
    test_asset_connectability_util.delay(asset)


def push_cluster_system_users_to_asset(asset):
    logger.info("Push cluster system user to asset: {}".format(asset))
    task_name = _("Push cluster system users to asset")
    system_users = asset.cluster.systemuser_set.all()
    push_system_user_util.delay(system_users, [asset], task_name)


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
def on_asset_created(sender, instance=None, created=False, **kwargs):
    if instance and created:
        logger.info("Asset `` create signal received".format(instance))
        update_asset_hardware_info_on_created(instance)
        test_asset_conn_on_created(instance)
        push_cluster_system_users_to_asset(instance)


@receiver(post_init, sender=Asset)
def on_asset_init(sender, instance, created=False, **kwargs):
    if instance and created is False:
        instance.__original_cluster = instance.cluster


@receiver(post_save, sender=Asset)
def on_asset_cluster_changed(sender, instance=None, created=False, **kwargs):
    if instance and created is False and instance.cluster != instance.__original_cluster:
        logger.info("Asset cluster changed signal received")
        push_cluster_system_users_to_asset(instance)


def push_to_cluster_assets_on_system_user_created_or_update(system_user):
    if not system_user.auto_push:
        return
    logger.debug("Push system user `{}` to cluster assets".format(system_user.name))
    for cluster in system_user.cluster.all():
        task_name = _("Push system user to cluster assets: {}->{}").format(
            cluster.name, system_user.name
        )
        assets = cluster.assets.all()
        push_system_user_util.delay([system_user], assets, task_name)


@receiver(post_save, sender=SystemUser)
def on_system_user_created_or_updated(sender, instance=None, **kwargs):
    if instance and instance.auto_push:
        logger.info("System user `{}` create or update signal received".format(instance))
        push_to_cluster_assets_on_system_user_created_or_update(instance)


@receiver(post_init, sender=Cluster, dispatch_uid="my_unique_identifier")
def on_cluster_init(sender, instance, **kwargs):
    instance.__original_assets = tuple(instance.assets.values_list('pk', flat=True))
    instance.__origin_system_users = tuple(instance.systemuser_set.values_list('pk', flat=True))


@receiver(post_save, sender=Cluster, dispatch_uid="my_unique_identifier")
def on_cluster_assets_changed(sender, instance, **kwargs):
    assets_origin = instance.__original_assets
    assets_new = instance.assets.values_list('pk', flat=True)
    assets_added = set(assets_new) - set(assets_origin)
    if assets_added:
        logger.debug("Receive cluster change assets signal")
        logger.debug("Push cluster `{}` system users to: {}".format(
            instance, ', '.join([str(asset) for asset in assets_added])
        ))
        assets = []
        for asset_id in assets_added:
            try:
                asset = Asset.objects.get(pk=asset_id)
            except Asset.DoesNotExist:
                continue
            else:
                assets.append(asset)
        system_users = [s for s in instance.systemuser_set.all() if s.auto_push]
        task_name = _("Push system user to assets")
        push_system_user_util.delay(system_users, assets, task_name)


@receiver(post_save, sender=Cluster, dispatch_uid="my_unique_identifier2")
def on_cluster_system_user_changed(sender, instance, **kwargs):
    system_users_origin = instance.__origin_system_users
    system_user_new = instance.systemuser_set.values_list('pk', flat=True)
    system_users_added = set(system_user_new) - set(system_users_origin)
    if system_users_added:
        logger.debug("Receive cluster change system users signal")
        system_users = []
        for system_user_id in system_users_added:
            try:
                system_user = SystemUser.objects.get(pk=system_user_id)
            except SystemUser.DoesNotExist:
                continue
            else:
                system_users.append(system_user)
        logger.debug("Push new system users `{}` to cluster `{}` assets".format(
            ','.join([s.name for s in system_users]), instance
        ))
        task_name = _(
            "Push system user to cluster assets: {}->{}").format(
             instance.name, ', '.join(s.name for s in system_users)
        )
        push_system_user_util.delay(system_users, instance.assets.all(), task_name)

