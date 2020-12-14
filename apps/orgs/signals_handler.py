# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.db.models.signals import m2m_changed
from django.db.models.signals import post_save
from django.dispatch import receiver

from orgs.utils import tmp_to_org
from .models import Organization, OrganizationMember
from .hands import set_current_org, Node, get_current_org
from perms.models import (AssetPermission, DatabaseAppPermission,
                          K8sAppPermission, RemoteAppPermission)
from users.models import UserGroup, User
from common.const.signals import PRE_REMOVE, POST_REMOVE


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


def _remove_users(model, users, org):
    with tmp_to_org(org):
        if not isinstance(users, (tuple, list, set)):
            users = (users, )

        m2m_model = model.users.through
        reverse = model.users.reverse
        if reverse:
            m2m_field_name = model.users.field.m2m_reverse_field_name()
        else:
            m2m_field_name = model.users.field.m2m_field_name()
        relations = m2m_model.objects.filter(**{
            'user__in': users, f'{m2m_field_name}__org_id': org.id
        })

        objs_id_users_id_map = defaultdict(set)

        for relation in relations:
            objs_id_users_id_map[getattr(relation, f'{m2m_field_name}_id')].add(relation.user_id)

        objs = model.objects.filter(id__in=objs_id_users_id_map.keys())
        for obj in objs:
            m2m_changed.send(
                sender=m2m_model, instance=obj, reverse=reverse, model=User,
                pk_set=objs_id_users_id_map[obj.id], using=model.objects.db, action=PRE_REMOVE
            )

        relations.delete()

        for obj in objs:
            m2m_changed.send(
                sender=m2m_model, instance=obj, reverse=reverse, model=User,
                pk_set=objs_id_users_id_map[obj.id], using=model.objects.db, action=POST_REMOVE
            )


def _clear_users_from_org(org, users):
    """
    清理用户在该组织下的相关数据
    """
    if not users:
        return

    models = (AssetPermission, DatabaseAppPermission,
              RemoteAppPermission, K8sAppPermission, UserGroup)

    for m in models:
        _remove_users(m, users, org)


@receiver(m2m_changed, sender=OrganizationMember)
def on_org_user_changed(action, instance, reverse, pk_set, **kwargs):
    if action == 'post_remove':
        if reverse:
            user = instance
            org_pk_set = pk_set

            orgs = Organization.objects.filter(id__in=org_pk_set)
            for org in orgs:
                if not org.members.filter(id=user.id).exists():
                    _clear_users_from_org(org, user)
        else:
            org = instance
            user_pk_set = pk_set

            leaved_users = set(pk_set) - set(org.members.filter(id__in=user_pk_set).values_list('id', flat=True))
            _clear_users_from_org(org, leaved_users)
