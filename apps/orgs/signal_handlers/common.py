# -*- coding: utf-8 -*-
#
from collections import defaultdict
from functools import partial

from django.conf import settings
from django.db.models.signals import post_save, pre_delete, m2m_changed, post_delete
from django.db.utils import ProgrammingError, OperationalError
from django.dispatch import receiver
from django.utils.functional import LazyObject

from common.const.signals import PRE_REMOVE, POST_REMOVE
from common.decorators import delay_run
from common.decorators import on_transaction_commit
from common.signals import django_ready
from common.utils import get_logger
from common.utils.connection import RedisPubSub
from orgs.hands import set_current_org, Node, get_current_org
from orgs.models import Organization
from orgs.utils import tmp_to_org, set_to_default_org
from perms.models import AssetPermission
from users.models import UserGroup, User
from users.signals import post_user_leave_org

logger = get_logger(__file__)


class OrgsMappingForMemoryPubSub(LazyObject):
    def _setup(self):
        self._wrapped = RedisPubSub('fm.orgs_mapping')


orgs_mapping_for_memory_pub_sub = OrgsMappingForMemoryPubSub()


def expire_orgs_mapping_for_memory(org_id):
    orgs_mapping_for_memory_pub_sub.publish(str(org_id))


@receiver(django_ready)
def subscribe_orgs_mapping_expire(sender, **kwargs):
    logger.debug("Start subscribe for expire orgs mapping from memory")

    if settings.DEBUG:
        try:
            set_to_default_org()
        except (ProgrammingError, OperationalError):
            pass

    orgs_mapping_for_memory_pub_sub.subscribe(
        lambda org_id: Organization.expire_orgs_mapping()
    )


@delay_run(ttl=5)
def expire_user_orgs():
    User.expire_users_rbac_perms_cache()


@receiver(post_save, sender=Organization)
def on_org_create(sender, instance, created=False, **kwargs):
    expire_user_orgs()


# 创建对应的root
@receiver(post_save, sender=Organization)
def on_org_create_or_update(sender, instance, **kwargs):
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
def delete_org_root_node_on_org_delete(sender, instance, **kwargs):
    expire_orgs_mapping_for_memory(instance.id)

    # 删除该组织下所有 节点
    with tmp_to_org(instance):
        root_node = Node.org_root()
        if root_node:
            root_node.delete()


@receiver(post_delete, sender=Organization)
def expire_user_orgs_on_org_delete(sender, instance, **kwargs):
    expire_user_orgs()


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
    default_org = Organization.default()
    with tmp_to_org(default_org):
        default_org.add_member(instance)
        default_group = UserGroup.objects.filter(name='Default').first()
        if default_group:
            default_group.users.add(instance)


def _remove_user_resource(model, users, org, user_field_name='users'):
    with tmp_to_org(org):
        if not isinstance(users, (tuple, list, set)):
            users = (users,)

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
            m2m_changed.send, sender=m2m_model, reverse=reverse,
            model=User, using=model.objects.db
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
    清理用户在该组织下的相关数据, 包括用户组, 资产授权, 用户授权
    """
    if not users:
        return

    models = (AssetPermission, UserGroup)

    for m in models:
        _remove_user_resource(m, users, org)


@receiver(post_user_leave_org)
def on_user_leave_org(sender, user=None, org=None, **kwargs):
    logger.debug('User leave org signal recv: {} <> {}'.format(user, org))
    _clear_users_from_org(org, [user])
