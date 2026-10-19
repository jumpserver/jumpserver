# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.dispatch import receiver

from common.signals import django_ready
from orgs.utils import tmp_to_root_org


@receiver(django_ready)
def set_assets_size_to_setting(sender, **kwargs):
    from assets.models import Asset
    try:
        with tmp_to_root_org():
            amount = Asset.objects.order_by().count()
    except Exception:
        amount = 0

    if amount > 20000:
        settings.ASSET_SIZE = 'large'
    elif amount > 5000:
        settings.ASSET_SIZE = 'medium'
