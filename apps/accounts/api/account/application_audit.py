from accounts import serializers
from accounts.models import ApplicationAudit
from common.drf.filters import DatetimeRangeFilterBackend
from orgs.mixins.api import OrgReadonlyModelViewSet

__all__ = ['ApplicationAuditViewSet']


class ApplicationAuditViewSet(OrgReadonlyModelViewSet):
    model = ApplicationAudit
    serializer_class = serializers.ApplicationAuditSerializer
    rbac_perms = {'list': 'audits.view_integrationapplicationlog', 'retrieve': 'audits.view_integrationapplicationlog'}
    filterset_fields = (
        'id', 'event', 'service', 'service_id', 'credential', 'credential_id',
        'credential_key', 'account', 'account_id', 'instance_id', 'operator',
        'remote_addr', 'source', 'result', 'revision', 'rotation_id', 'operation_id', 'summary',
    )
    search_fields = ('id', 'service', 'service_id', 'credential', 'credential_key',
                     'account', 'instance_id', 'operator', 'remote_addr', 'summary')
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [('date_created', ('date_from', 'date_to'))]
    ordering_fields = ('date_created',)
    ordering = ['-date_created', '-id']

    def get_queryset(self):
        queryset = super().get_queryset()
        excluded_event = self.request.query_params.get('exclude_event')
        if excluded_event:
            queryset = queryset.exclude(event=excluded_event)
        application = self.request.query_params.get('application')
        if application:
            queryset = queryset.filter(
                application_relations__application_id=application
            ).distinct()
        return queryset
