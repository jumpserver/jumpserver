# -*- coding: utf-8 -*-
#

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from common.utils import get_logger
from .models import NodePermission


logger = get_logger(__file__)


@receiver(post_save, sender=NodePermission, dispatch_uid="my_unique_identifier")
def on_asset_permission_create_or_update(sender, instance=None, **kwargs):
    if instance and instance.node and instance.system_user:
        instance.system_user.nodes.add(instance.node)

