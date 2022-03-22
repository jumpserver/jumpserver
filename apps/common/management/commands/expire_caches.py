from django.core.management.base import BaseCommand

from assets.signal_handlers.node_assets_mapping import expire_node_assets_mapping_for_memory
from orgs.caches import OrgResourceStatisticsCache
from orgs.models import Organization


def expire_node_assets_mapping():
    org_ids = Organization.objects.all().values_list('id', flat=True)
    org_ids = [*org_ids, '00000000-0000-0000-0000-000000000000']

    for org_id in org_ids:
        expire_node_assets_mapping_for_memory(org_id)


def expire_org_resource_statistics_cache():
    orgs = Organization.objects.all()
    for org in orgs:
        cache = OrgResourceStatisticsCache(org)
        cache.expire()


class Command(BaseCommand):
    help = 'Expire caches'

    def handle(self, *args, **options):
        expire_node_assets_mapping()
        expire_org_resource_statistics_cache()
