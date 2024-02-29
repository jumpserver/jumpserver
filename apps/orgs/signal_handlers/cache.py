from django.db.models.signals import post_save, pre_delete, pre_save, post_delete
from django.dispatch import receiver

from accounts.models import Account
from assets.models import Asset, Domain
from assets.models import Node
from common.decorators import merge_delay_run
from common.utils import get_logger
from orgs.caches import OrgResourceStatisticsCache
from orgs.models import Organization
from orgs.utils import current_org
from perms.models import AssetPermission
from rbac.models import OrgRoleBinding, SystemRoleBinding, RoleBinding
from terminal.models import Session
from users.models import UserGroup, User
from users.signals import pre_user_leave_org

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


def refresh_all_orgs_user_amount_cache(user):
    orgs = user.orgs.distinct()
    for org in orgs:
        refresh_cache('users_amount', org)
        refresh_cache('new_users_amount_this_week', org)


@receiver(post_save, sender=OrgRoleBinding)
def on_user_create_or_invite_refresh_cache(sender, instance, created, **kwargs):
    if created:
        refresh_cache('users_amount', instance.org)
        refresh_cache('new_users_amount_this_week', instance.org)


@receiver(post_save, sender=SystemRoleBinding)
def on_user_global_create_refresh_cache(sender, instance, created, **kwargs):
    if created and current_org.is_root():
        refresh_cache('users_amount', current_org)
        refresh_cache('new_users_amount_this_week', current_org)


@receiver(pre_user_leave_org)
def on_user_remove_refresh_cache(sender, org=None, **kwargs):
    refresh_cache('users_amount', org)
    refresh_cache('new_users_amount_this_week', org)


@receiver(pre_delete, sender=User)
def on_user_delete_refresh_cache(sender, instance, **kwargs):
    refresh_all_orgs_user_amount_cache(instance)


model_cache_field_mapper = {
    Node: ['nodes_amount'],
    Domain: ['domains_amount'],
    UserGroup: ['groups_amount'],
    Account: ['accounts_amount'],
    RoleBinding: ['users_amount', 'new_users_amount_this_week'],
    Asset: ['assets_amount', 'new_assets_amount_this_week'],
    AssetPermission: ['asset_perms_amount'],
}


class OrgResourceStatisticsRefreshUtil:
    @staticmethod
    @merge_delay_run(ttl=30)
    def refresh_org_fields(org_fields=()):
        for org, cache_field_name in org_fields:
            OrgResourceStatisticsCache(org).expire(*cache_field_name)
            OrgResourceStatisticsCache(Organization.root()).expire(*cache_field_name)

    @classmethod
    def refresh_if_need(cls, instance):
        cache_field_name = model_cache_field_mapper.get(type(instance))
        if not cache_field_name:
            return
        org = getattr(instance, 'org', None)
        cache_field_name = tuple(cache_field_name)
        cls.refresh_org_fields.delay(org_fields=((org, cache_field_name),))


@receiver(post_save)
def on_post_save_refresh_org_resource_statistics_cache(sender, instance, created, **kwargs):
    if created:
        OrgResourceStatisticsRefreshUtil.refresh_if_need(instance)


@receiver(post_delete)
def on_post_delete_refresh_org_resource_statistics_cache(sender, instance, **kwargs):
    OrgResourceStatisticsRefreshUtil.refresh_if_need(instance)


def _refresh_session_org_resource_statistics_cache(instance: Session):
    cache_field_name = [
        'total_count_online_users', 'total_count_online_sessions',
        'total_count_today_active_assets', 'total_count_today_failed_sessions'
    ]

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
