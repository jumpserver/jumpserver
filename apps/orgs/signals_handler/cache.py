from django.db.models.signals import m2m_changed
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from orgs.models import Organization, OrganizationMember
from assets.models import Node
from perms.models import (AssetPermission, ApplicationPermission)
from users.models import UserGroup, User
from applications.models import Application
from terminal.models import Session
from assets.models import Asset, AdminUser, SystemUser, Domain, Gateway
from common.const.signals import POST_PREFIX
from orgs.caches import OrgResourceStatisticsCache


def refresh_user_amount_on_user_create_or_delete(user_id):
    orgs = Organization.objects.filter(m2m_org_members__user_id=user_id).distinct()
    for org in orgs:
        org_cache = OrgResourceStatisticsCache(org)
        org_cache.expire('users_amount')
    OrgResourceStatisticsCache(Organization.root()).expire('users_amount')


@receiver(post_save, sender=User)
def on_user_create_refresh_cache(sender, instance, created, **kwargs):
    if created:
        refresh_user_amount_on_user_create_or_delete(instance.id)


@receiver(pre_delete, sender=User)
def on_user_delete_refresh_cache(sender, instance, **kwargs):
    refresh_user_amount_on_user_create_or_delete(instance.id)


@receiver(m2m_changed, sender=OrganizationMember)
def on_org_user_changed_refresh_cache(sender, action, instance, reverse, pk_set, **kwargs):
    if not action.startswith(POST_PREFIX):
        return

    if reverse:
        orgs = Organization.objects.filter(id__in=pk_set)
    else:
        orgs = [instance]

    for org in orgs:
        org_cache = OrgResourceStatisticsCache(org)
        org_cache.expire('users_amount')
    OrgResourceStatisticsCache(Organization.root()).expire('users_amount')


class OrgResourceStatisticsRefreshUtil:
    model_cache_field_mapper = {
        ApplicationPermission: ['app_perms_amount'],
        AssetPermission: ['asset_perms_amount'],
        Application: ['applications_amount'],
        Gateway: ['gateways_amount'],
        Domain: ['domains_amount'],
        SystemUser: ['system_users_amount'],
        AdminUser: ['admin_users_amount'],
        Node: ['nodes_amount'],
        Asset: ['assets_amount'],
        UserGroup: ['groups_amount'],
        Session: ['total_count_online_users', 'total_count_online_sessions']
    }

    @classmethod
    def refresh_if_need(cls, instance):
        cache_field_name = cls.model_cache_field_mapper.get(type(instance))
        if cache_field_name:
            org_cache = OrgResourceStatisticsCache(instance.org)
            org_cache.expire(*cache_field_name)
            OrgResourceStatisticsCache(Organization.root()).expire(*cache_field_name)


@receiver(pre_save)
def on_post_save_refresh_org_resource_statistics_cache(sender, instance, **kwargs):
    OrgResourceStatisticsRefreshUtil.refresh_if_need(instance)


@receiver(pre_delete)
def on_pre_delete_refresh_org_resource_statistics_cache(sender, instance, **kwargs):
    OrgResourceStatisticsRefreshUtil.refresh_if_need(instance)
