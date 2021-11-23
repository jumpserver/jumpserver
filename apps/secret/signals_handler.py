# -*- coding: utf-8 -*-
#
from django.dispatch import receiver
from django.conf import settings
from django.db.models.signals import pre_save, post_save, post_delete

from assets.models import BaseUser
from common.utils import get_logger
from .backends import Secret

logger = get_logger(__name__)


@receiver(pre_save)
def clear_secret(sender, instance=None, **kwargs):
    if issubclass(sender, BaseUser):
        backend = settings.SECRET_STORAGE_BACKEND
        try:
            client = Secret(instance, backend)
            client.clear_secret()
            storage_type = getattr(instance, 'storage_type')
            setattr(instance, '_storage_type', storage_type)
            setattr(instance, 'storage_type', backend)
            setattr(instance, backend, client)
        except ModuleNotFoundError:
            logger.debug(
                "Secret key storage configuration DB: CU-{}".format(instance.pk)
            )


@receiver(post_save)
def update_or_create_secret(sender, instance=None, created=None, **kwargs):
    if issubclass(sender, BaseUser):
        backend = settings.SECRET_STORAGE_BACKEND
        if hasattr(instance, backend):
            client = getattr(instance, backend)
            if created:
                client.update_or_create_secret()
            else:
                if getattr(instance, '_storage_type') == backend:
                    old_secret_data = client.get_secret()
                    client.patch_secret(old_secret_data)
                else:
                    client.update_or_create_secret()


@receiver(post_delete)
def delete_secret(sender, instance=None, **kwargs):
    if issubclass(sender, BaseUser):
        backend = settings.SECRET_STORAGE_BACKEND
        try:
            client = Secret(instance, backend)
            client.delete_secret()
        except ModuleNotFoundError:
            logger.debug(
                "Secret key storage configuration DB: D-{}".format(instance.pk)
            )
