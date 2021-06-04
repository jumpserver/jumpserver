# -*- coding: utf-8 -*-
#
import threading
from collections import defaultdict
from functools import partial

from django.dispatch import receiver
from django.utils.functional import LazyObject
from django.db.models.signals import m2m_changed
from django.db.models.signals import post_save, post_delete, pre_delete

from orgs.utils import tmp_to_org
from orgs.models import Organization, OrganizationMember
from orgs.hands import set_current_org, Node, get_current_org
from perms.models import (AssetPermission, ApplicationPermission)
from users.models import UserGroup, User
from common.const.signals import PRE_REMOVE, POST_REMOVE
from common.signals import django_ready
from common.utils import get_logger
from common.utils.connection import RedisPubSub


logger = get_logger(__file__)


def get_orgs_mapping_for_memory_pub_sub():
    return RedisPubSub('fm.orgs_mapping')


class OrgsMappingForMemoryPubSub(LazyObject):
    def _setup(self):
        self._wrapped = get_orgs_mapping_for_memory_pub_sub()


orgs_mapping_for_memory_pub_sub = OrgsMappingForMemoryPubSub()


def expire_orgs_mapping_for_memory():
    orgs_mapping_for_memory_pub_sub.publish('expire_orgs_mapping')


@receiver(django_ready)
def subscribe_orgs_mapping_expire(sender, **kwargs):
    logger.debug("Start subscribe for expire orgs mapping from memory")

    def keep_subscribe():
        while True:
            try:
                subscribe = orgs_mapping_for_memory_pub_sub.subscribe()
                for message in subscribe.listen():
                    if message['type'] != 'message':
                        continue
                    if message['data'] == b'error':
                        raise ValueError
                    Organization.expire_orgs_mapping()
                    logger.debug('Expire orgs mapping')
            except Exception as e:
                logger.exception(f'subscribe_orgs_mapping_expire: {e}')
                Organization.expire_orgs_mapping()

    t = threading.Thread(target=keep_subscribe)
    t.daemon = True
    t.start()


@receiver(post_save, sender=Organization)
def on_org_create_or_update(sender, instance=None, created=False, **kwargs):
    # 必须放到最开始, 因为下面调用Node.save方法时会获取当前组织的org_id(即instance.org_id), 如果不过期会找不到
    expire_orgs_mapping_for_memory()
    if instance:
        old_org = get_current_org()
        set_current_org(instance)
        node_root = Node.org_root()
        if node_root.value != instance.name:
            node_root.value = instance.name
            node_root.save()
        set_current_org(old_org)


@receiver(post_delete, sender=Organization)
def on_org_delete(sender, **kwargs):
    expire_orgs_mapping_for_memory()


@receiver(pre_delete, sender=Organization)
def on_org_delete(sender, instance, **kwargs):
    # 删除该组织下所有 节点
    with tmp_to_org(instance):
        root_node = Node.org_root()
        if root_node:
            root_node.delete()


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
            'user__in': users,
            f'{m2m_field_name}__org_id': org.id
        })

        object_id_user_ids_map = defaultdict(set)

        m2m_field_attr_name = f'{m2m_field_name}_id'
        for relation in relations:
            object_id = getattr(relation, m2m_field_attr_name)
            object_id_user_ids_map[object_id].add(relation.user_id)

        objects = model.objects.filter(id__in=object_id_user_ids_map.keys())
        send_m2m_change_signal = partial(
            m2m_changed.send,
            sender=m2m_model, reverse=reverse, model=User, using=model.objects.db
        )

        for obj in objects:
            send_m2m_change_signal(
                instance=obj,
                pk_set=object_id_user_ids_map[obj.id],
                action=PRE_REMOVE
            )

        relations.delete()

        for obj in objects:
            send_m2m_change_signal(
                instance=obj,
                pk_set=object_id_user_ids_map[obj.id],
                action=POST_REMOVE
            )


def _clear_users_from_org(org, users):
    """
    清理用户在该组织下的相关数据
    """
    if not users:
        return

    models = (AssetPermission, ApplicationPermission, UserGroup)

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
