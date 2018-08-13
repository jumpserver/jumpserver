# -*- coding: utf-8 -*-
#

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Organization


@receiver(post_save, sender=Organization)
def on_org_update(sender, instance=None, created=False, **kwargs):
    if instance and not created:
        instance.expire_cache()
