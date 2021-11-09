# -*- coding: utf-8 -*-
#
from django.dispatch import receiver
from django.db.models import Model
from django.db.models.signals import post_save, post_delete

from .utils import is_model_setting_vault_field_and_active


@receiver(post_save)
def created_or_update_secret(sender: Model, instance=None, **kwargs):
    if is_model_setting_vault_field_and_active(sender):
        secret_data = {k: getattr(instance, k) for k in getattr(sender, 'VAULT_FIELD')}
        getattr(sender, 'secret').update_or_create(instance.pk, secret_data)


@receiver(post_delete)
def complete_delete_secret_secret(sender: Model, instance=None, **kwargs):
    if is_model_setting_vault_field_and_active(sender):
        getattr(sender, 'secret').complete_delete_secret(instance.pk)
