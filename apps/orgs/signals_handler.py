# -*- coding: utf-8 -*-
#

from django.db.models.signals import m2m_changed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Organization
from .hands import set_current_org, current_org, Node
from perms.models import AssetPermission
from users.models import UserGroup


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


@receiver(m2m_changed, sender=Organization.users.through)
def on_org_user_changed(sender, instance=None, **kwargs):
    if isinstance(instance, Organization):
        old_org = current_org
        set_current_org(instance)
        if kwargs['action'] == 'pre_remove':
            users = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
            for user in users:
                perms = AssetPermission.objects.filter(users=user)
                user_groups = UserGroup.objects.filter(users=user)
                for perm in perms:
                    perm.users.remove(user)
                for user_group in user_groups:
                    user_group.users.remove(user)
        set_current_org(old_org)
