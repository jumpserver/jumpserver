# -*- coding: utf-8 -*-
#

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction

from jumpserver.utils import current_request
from common.utils import get_request_ip
from .models import OperateLog

MODELS_NEED_RECORD = (
    'User', 'UserGroup', 'Asset', 'Node', 'AdminUser', 'SystemUser',
    'Domain', 'Gateway', 'Organization', 'AssetPermission',
)


def create_operate_log(action, sender, resource):
    user = current_request.user if current_request else None
    if not user or not user.is_authenticated:
        return
    model_name = sender._meta.object_name
    if model_name not in MODELS_NEED_RECORD:
        return
    resource_type = sender._meta.verbose_name
    remote_addr = get_request_ip(current_request)
    with transaction.atomic():
        OperateLog.objects.create(
            user=user, action=action, resource_type=resource_type,
            resource=resource, remote_addr=remote_addr
        )


@receiver(post_save, dispatch_uid="my_unique_identifier")
def on_asset_created_or_update(sender, instance=None, created=False, **kwargs):
    if created:
        action = OperateLog.ACTION_CREATE
    else:
        action = OperateLog.ACTION_UPDATE
    create_operate_log(action, sender, instance)

