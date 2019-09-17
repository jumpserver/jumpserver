# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext as _

from common.utils import get_logger


logger = get_logger(__file__)
__all__ = [
    'check_asset_can_run_ansible', 'clean_hosts', 'clean_hosts_by_protocol'
]


def check_asset_can_run_ansible(asset):
    if not asset.is_active:
        msg = _("Asset has been disabled, skipped: {}").format(asset)
        logger.info(msg)
        return False
    if not asset.is_support_ansible():
        msg = _("Asset may not be support ansible, skipped: {}").format(asset)
        logger.info(msg)
        return False
    return True


def clean_hosts(assets):
    clean_assets = []
    for asset in assets:
        if not check_asset_can_run_ansible(asset):
            continue
        clean_assets.append(asset)
    if not clean_assets:
        logger.info(_("No assets matched, stop task"))
    return clean_assets


def clean_hosts_by_protocol(system_user, assets):
    hosts = [
        asset for asset in assets
        if asset.has_protocol(system_user.protocol)
    ]
    if not hosts:
        msg = _("No assets matched related system user protocol, stop task")
        logger.info(msg)
    return hosts
