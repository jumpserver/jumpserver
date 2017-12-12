# -*- coding: utf-8 -*-
#

from django.dispatch import Signal, receiver

from common.utils import get_logger

logger = get_logger(__file__)
on_asset_created = Signal(providing_args=['asset'])
on_app_ready = Signal()


@receiver(on_asset_created)
def update_asset_info(sender, asset=None, **kwargs):
    from .tasks import update_assets_hardware_info
    logger.debug("Receive asset create signal, update asset hardware info")
    update_assets_hardware_info.delay([asset])


@receiver(on_asset_created)
def test_admin_user_connective(sender, asset=None, **kwargs):
    from .tasks import test_admin_user_connectability_manual
    logger.debug("Receive asset create signal, test admin user connectability")
    test_admin_user_connectability_manual.delay(asset)


@receiver(on_app_ready)
def test_admin_user_on_app_ready(sender, **kwargs):
    from .tasks import test_admin_user_connectability_period
    logger.debug("Receive app ready signal, test admin connectability")
    test_admin_user_connectability_period.delay()
