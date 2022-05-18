from functools import wraps
from django.db.models.signals import post_save, pre_delete, pre_save, post_delete
from django.dispatch import receiver

from orgs.models import Organization
from assets.models import Node
from perms.models import AssetPermission, ApplicationPermission
from users.models import UserGroup, User
from users.signals import pre_user_leave_org
from applications.models import Application
from terminal.models import Session
from rbac.models import OrgRoleBinding, SystemRoleBinding, RoleBinding
from assets.models import Asset, SystemUser, Domain, Gateway
from orgs.caches import OrgResourceStatisticsCache
from orgs.utils import current_org
from common.utils import get_logger

logger = get_logger(__name__)


def refresh_cache(name, org):
    names = None
    if isinstance(name, (str,)):
        names = [name, ]
    if isinstance(names, (list, tuple)):
        for name in names:
            OrgResourceStatisticsCache(org).expire(name)
            OrgResourceStatisticsCache(Organization.root()).expire(name)
    else:
        logger.warning('refresh cache fail: {}'.format(name))


def refresh_user_amount_cache(user):
    orgs = user.orgs.distinct()
    for org in orgs:
        refresh_cache('users_amount', org)


@receiver(post_save, sender=OrgRoleBinding)
def on_user_create_or_invite_refresh_cache(sender, instance, created, **kwargs):
    if created:
        refresh_cache('users_amount', instance.org)


@receiver(post_save, sender=SystemRoleBinding)
def on_user_global_create_refresh_cache(sender, instance, created, **kwargs):
    if created and current_org.is_root():
        refresh_cache('users_amount', current_org)


@receiver(pre_user_leave_org)
def on_user_remove_refresh_cache(sender, org=None, **kwargs):
    refresh_cache('users_amount', org)


@receiver(pre_delete, sender=User)
def on_user_delete_refresh_cache(sender, instance, **kwargs):
    refresh_user_amount_cache(instance)


# @receiver(m2m_changed, sender=OrganizationMember)
# def on_org_user_changed_refresh_cache(sender, action, instance, reverse, pk_set, **kwargs):
#     if not action.startswith(POST_PREFIX):
#         return
#
#     if reverse:
#         orgs = Organization.objects.filter(id__in=pk_set)
#     else:
#         orgs = [instance]
#
#     for org in orgs:
#         org_cache = OrgResourceStatisticsCache(org)
#         org_cache.expire('users_amount')
#     OrgResourceStatisticsCache(Organization.root()).expire('users_amount')


class OrgResourceStatisticsRefreshUtil:
    model_cache_field_mapper = {
        ApplicationPermission: ['app_perms_amount'],
        AssetPermission: ['asset_perms_amount'],
        Application: ['applications_amount'],
        Gateway: ['gateways_amount'],
        Domain: ['domains_amount'],
        SystemUser: ['system_users_amount', 'admin_users_amount'],
        Node: ['nodes_amount'],
        Asset: ['assets_amount'],
        UserGroup: ['groups_amount'],
        RoleBinding: ['users_amount']
    }

    @classmethod
    def refresh_if_need(cls, instance):
        cache_field_name = cls.model_cache_field_mapper.get(type(instance))
        if not cache_field_name:
            return
        OrgResourceStatisticsCache(Organization.root()).expire(*cache_field_name)
        if instance.org:
            OrgResourceStatisticsCache(instance.org).expire(*cache_field_name)


@receiver(post_save)
def on_post_save_refresh_org_resource_statistics_cache(sender, instance, created, **kwargs):
    if created:
        OrgResourceStatisticsRefreshUtil.refresh_if_need(instance)


@receiver(post_delete)
def on_post_delete_refresh_org_resource_statistics_cache(sender, instance, **kwargs):
    OrgResourceStatisticsRefreshUtil.refresh_if_need(instance)


def _refresh_session_org_resource_statistics_cache(instance: Session):
    cache_field_name = ['total_count_online_users', 'total_count_online_sessions']

    org_cache = OrgResourceStatisticsCache(instance.org)
    org_cache.expire(*cache_field_name)
    OrgResourceStatisticsCache(Organization.root()).expire(*cache_field_name)


@receiver(pre_save, sender=Session)
def on_session_pre_save(sender, instance: Session, **kwargs):
    old = Session.objects.filter(id=instance.id).values_list('is_finished', flat=True)
    if old:
        instance._signal_old_is_finished = old[0]
    else:
        instance._signal_old_is_finished = None


@receiver(post_save, sender=Session)
def on_session_changed_refresh_org_resource_statistics_cache(sender, instance, created, **kwargs):
    if created or instance.is_finished != instance._signal_old_is_finished:
        _refresh_session_org_resource_statistics_cache(instance)


@receiver(post_delete, sender=Session)
def on_session_deleted_refresh_org_resource_statistics_cache(sender, instance, **kwargs):
    _refresh_session_org_resource_statistics_cache(instance)
