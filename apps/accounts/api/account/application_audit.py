from accounts import serializers
from accounts.models import ApplicationAudit
from common.drf.filters import DatetimeRangeFilterBackend
from orgs.mixins.api import OrgReadonlyModelViewSet

__all__ = ['ApplicationAuditViewSet']


class ApplicationAuditViewSet(OrgReadonlyModelViewSet):
    model = ApplicationAudit
    serializer_class = serializers.ApplicationAuditSerializer
    rbac_perms = {'list': 'audits.view_integrationapplicationlog', 'retrieve': 'audits.view_integrationapplicationlog'}
    filterset_fields = ('event', 'result', 'source', 'service_id', 'credential_id')
    search_fields = ('service', 'credential', 'credential_key', 'configuration', 'instance_id', 'operator', 'summary')
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [('date_created', ('date_from', 'date_to'))]
    ordering_fields = ('date_created',)
    ordering = ['-date_created', '-id']
