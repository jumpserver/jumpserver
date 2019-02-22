# -*- coding: utf-8 -*-
#

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction

from jumpserver.utils import current_request
from common.utils import get_request_ip, get_logger
from users.models import User
from .models import OperateLog, PasswordChangeLog

logger = get_logger(__name__)


MODELS_NEED_RECORD = (
    'User', 'UserGroup', 'Asset', 'Node', 'AdminUser', 'SystemUser',
    'Domain', 'Gateway', 'Organization', 'AssetPermission', 'CommandFilter',
    'CommandFilterRule', 'License', 'Setting', 'Account', 'SyncInstanceTask',
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

    data = {
        "user": str(user), 'action': action, 'resource_type': resource_type,
        'resource': str(resource), 'remote_addr': remote_addr,
    }
    with transaction.atomic():
        try:
            OperateLog.objects.create(**data)
        except Exception as e:
            logger.error("Create operate log error: {}".format(e))


@receiver(post_save, dispatch_uid="my_unique_identifier")
def on_object_created_or_update(sender, instance=None, created=False, **kwargs):
    if created:
        action = OperateLog.ACTION_CREATE
    else:
        action = OperateLog.ACTION_UPDATE
    create_operate_log(action, sender, instance)


@receiver(post_delete, dispatch_uid="my_unique_identifier")
def on_object_delete(sender, instance=None, **kwargs):
    create_operate_log(OperateLog.ACTION_DELETE, sender, instance)


@receiver(post_save, sender=User, dispatch_uid="my_unique_identifier")
def on_user_change_password(sender, instance=None, **kwargs):
    if hasattr(instance, '_set_password'):
        if not current_request or not current_request.user.is_authenticated:
            return
        with transaction.atomic():
            PasswordChangeLog.objects.create(
                user=instance, change_by=current_request.user,
                remote_addr=get_request_ip(current_request),
            )
