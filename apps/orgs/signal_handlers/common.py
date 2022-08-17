# -*- coding: utf-8 -*-
#
import threading
from collections import defaultdict
from functools import partial

from django.dispatch import receiver
from django.utils.functional import LazyObject
from django.db.models.signals import m2m_changed
from django.db.models.signals import post_save, pre_delete

from orgs.utils import tmp_to_org
from orgs.models import Organization
from orgs.hands import set_current_org, Node, get_current_org
from perms.models import (AssetPermission, ApplicationPermission)
from users.models import UserGroup, User
from assets.models import SystemUser
from common.const.signals import PRE_REMOVE, POST_REMOVE
from common.decorator import on_transaction_commit
from common.signals import django_ready
from common.utils import get_logger
from common.utils.connection import RedisPubSub
from assets.models import CommandFilterRule
from users.signals import post_user_leave_org


logger = get_logger(__file__)


def get_orgs_mapping_for_memory_pub_sub():
    return RedisPubSub('fm.orgs_mapping')


class OrgsMappingForMemoryPubSub(LazyObject):
    def _setup(self):
        self._wrapped = get_orgs_mapping_for_memory_pub_sub()


orgs_mapping_for_memory_pub_sub = OrgsMappingForMemoryPubSub()


def expire_orgs_mapping_for_memory(org_id):
    orgs_mapping_for_memory_pub_sub.publish(str(org_id))


@receiver(django_ready)
def subscribe_orgs_mapping_expire(sender, **kwargs):
    logger.debug("Start subscribe for expire orgs mapping from memory")

    def keep_subscribe_org_mapping():
        orgs_mapping_for_memory_pub_sub.subscribe(
            lambda org_id: Organization.expire_orgs_mapping()
        )

    t = threading.Thread(target=keep_subscribe_org_mapping)
    t.daemon = True
    t.start()


# 创建对应的root
@receiver(post_save, sender=Organization)
def on_org_create_or_update(sender, instance, created=False, **kwargs):
    # 必须放到最开始, 因为下面调用Node.save方法时会获取当前组织的org_id(即instance.org_id), 如果不过期会找不到
    expire_orgs_mapping_for_memory(instance.id)
    old_org = get_current_org()
    set_current_org(instance)
    node_root = Node.org_root()
    if node_root.value != instance.name:
        node_root.value = instance.name
        node_root.save()
    set_current_org(old_org)


@receiver(pre_delete, sender=Organization)
def on_org_delete(sender, instance, **kwargs):
    expire_orgs_mapping_for_memory(instance.id)

    # 删除该组织下所有 节点
    with tmp_to_org(instance):
        root_node = Node.org_root()
        if root_node:
            root_node.delete()


def _remove_users(model, users, org, user_field_name='users'):
    with tmp_to_org(org):
        if not isinstance(users, (tuple, list, set)):
            users = (users, )

        user_field = getattr(model, user_field_name)
        m2m_model = user_field.through
        reverse = user_field.reverse
        if reverse:
            m2m_field_name = user_field.field.m2m_reverse_field_name()
        else:
            m2m_field_name = user_field.field.m2m_field_name()
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

    models = (AssetPermission, ApplicationPermission, UserGroup, SystemUser)

    for m in models:
        _remove_users(m, users, org)

    _remove_users(CommandFilterRule, users, org, user_field_name='reviewers')


@receiver(post_save, sender=User)
@on_transaction_commit
def on_user_created_set_default_org(sender, instance, created, **kwargs):
    if not instance.id:
        # 用户已被手动删除，instance.orgs 时会使用 id 进行查找报错，所以判断不存在id时不做处理
        return
    if not created:
        return
    if instance.orgs.count() > 0:
        return
    with tmp_to_org(Organization.default()):
        Organization.default().add_member(instance)


@receiver(post_user_leave_org)
def on_user_leave_org(sender, user=None, org=None, **kwargs):
    logger.debug('User leave org signal recv: {} <> {}'.format(user, org))
    _clear_users_from_org(org, [user])
