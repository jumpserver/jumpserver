# -*- coding: utf-8 -*-
#

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Organization
from .hands import set_current_org, current_org, Node


@receiver(post_save, sender=Organization)
def on_org_create_or_update(sender, instance=None, created=False, **kwargs):
    if instance:
        old_org = current_org
        set_current_org(instance)
        node_root = Node.root()
        if node_root.value != instance.name:
            node_root.value = instance.name
            node_root.save()
        set_current_org(old_org)

    if instance and not created:
        instance.expire_cache()
