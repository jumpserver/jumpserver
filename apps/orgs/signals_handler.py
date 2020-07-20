# -*- coding: utf-8 -*-
#

from django.db.models.signals import m2m_changed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Organization, OrganizationMember
from .hands import set_current_org, current_org, Node, get_current_org
from perms.models import AssetPermission
from users.models import UserGroup


@receiver(post_save, sender=Organization)
def on_org_create_or_update(sender, instance=None, created=False, **kwargs):
    if instance:
        old_org = get_current_org()
        set_current_org(instance)
        node_root = Node.org_root()
        if node_root.value != instance.name:
            node_root.value = instance.name
            node_root.save()
        set_current_org(old_org)

    if instance and not created:
        instance.expire_cache()


def _remove_users(model, users, org, reverse=False):
    if not isinstance(users, (tuple, list, set)):
        users = (users, )

    m2m_model = model.users.through
    if reverse:
        m2m_field_name = model.users.field.m2m_reverse_field_name()
    else:
        m2m_field_name = model.users.field.m2m_field_name()
    m2m_model.objects.filter(**{'user__in': users, f'{m2m_field_name}__org_id': org.id}).delete()


def _clear_users_from_org(org, users):
    if not users:
        return

    old_org = current_org
    set_current_org(org)
    _remove_users(AssetPermission, users, org)
    _remove_users(UserGroup, users, org, reverse=True)
    set_current_org(old_org)


@receiver(m2m_changed, sender=OrganizationMember)
def on_org_user_changed(sender, instance=None, action=None, pk_set=None, **kwargs):
    if action == 'post_remove':
        leaved_users = set(pk_set) - set(instance.members.values_list('id', flat=True))
        _clear_users_from_org(instance, leaved_users)
