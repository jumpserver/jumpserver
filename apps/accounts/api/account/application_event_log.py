from collections import defaultdict
from uuid import UUID

from django.db.models import Case, CharField, F, OuterRef, Subquery, Value, When
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from accounts import serializers
from accounts.const import ApplicationCommandEvent, ApplicationEvent
from accounts.models import ApplicationAudit, ApplicationCommand, ApplicationEventDelivery, CredentialRotationEvent
from common.drf.filters import DatetimeRangeFilterBackend
from orgs.mixins.api import OrgReadonlyModelViewSet

__all__ = ['ApplicationEventLogViewSet']


class ApplicationEventLogViewSet(OrgReadonlyModelViewSet):
    model = ApplicationAudit
    serializer_class = serializers.ApplicationEventLogSerializer
    rbac_perms = {
        'list': 'audits.view_integrationapplicationlog',
        'retrieve': 'audits.view_integrationapplicationlog',
    }
    filterset_fields = ('id', 'service', 'service_id', 'credential', 'credential_id', 'account', 'account_id', 'operator')
    search_fields = ('id', 'service', 'credential', 'account', 'operator', 'protocol_event')
    ordering_fields = ('published_at',)
    ordering = ['-published_at', '-id']
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [('published_at', ('date_from', 'date_to'))]

    def get_queryset(self):
        notifications = CredentialRotationEvent.objects.filter(
            source_event_id=OuterRef('id'), org_id=OuterRef('org_id'),
        )
        queryset = super().get_queryset().annotate(
            protocol_event=Coalesce(Subquery(notifications.values('event')[:1]), F('command__event')),
            published_at=Coalesce(Subquery(notifications.values('published_at')[:1]), F('command__date_created')),
            event_source=Case(When(command__isnull=False, then=Value('manual')),
                              default=Value('automatic'), output_field=CharField()),
        ).filter(protocol_event__isnull=False)
        params = self.request.query_params
        # Filter the protocol code, never ApplicationAudit.event (the activity
        # type used as the source of this notification).
        codes = [code for value in params.getlist('event') + params.getlist('event__in')
                 for code in value.split(',') if code]
        if codes:
            supported = set(ApplicationEvent.values) | set(ApplicationCommandEvent.values)
            if not set(codes) <= supported:
                raise ValidationError({'event': _('Unsupported application event type.')})
            queryset = queryset.filter(protocol_event__in=codes)
        source = params.get('event_source')
        if source:
            if source not in ('manual', 'automatic'):
                raise ValidationError({'event_source': _('Unsupported application event source.')})
            queryset = queryset.filter(event_source=source)
        if params.get('application'):
            try:
                application_id = UUID(params['application'])
            except ValueError:
                raise ValidationError({'application': _('Invalid application ID.')})
            queryset = queryset.filter(application_relations__application_id=application_id).distinct()
        return queryset

    def get_serializer(self, instance=None, *args, **kwargs):
        context = kwargs.setdefault('context', self.get_serializer_context())
        rows = list(instance) if kwargs.get('many') else [instance] if instance else []
        ids = [row.id for row in rows]
        orgs = {row.org_id for row in rows}
        records = {event.source_event_id: event for event in CredentialRotationEvent.objects.filter(
            source_event_id__in=ids, org_id__in=orgs,
        )}
        records.update({command.source_event_id: command for command in ApplicationCommand.objects.filter(
            source_event_id__in=ids, org_id__in=orgs,
        ).select_related('source_event')})
        # The common paginator reloads model objects after selecting page IDs,
        # so query annotations must be restored from the frozen event records.
        for row in rows:
            event = records[row.id]
            row.protocol_event = event.event
            row.event_source = 'manual' if isinstance(event, ApplicationCommand) else 'automatic'
            row.published_at = event.date_created if row.event_source == 'manual' else event.published_at
        deliveries = defaultdict(list)
        for delivery in ApplicationEventDelivery.objects.filter(event_id__in=ids, org_id__in=orgs).select_related('audit').prefetch_related('attempts'):
            deliveries[delivery.event_id].append(delivery)
        application = self.request.query_params.get('application')
        context.update(protocol_records=records, webhook_deliveries=deliveries,
                       application_id=str(UUID(application)) if application else None)
        return super().get_serializer(rows if kwargs.get('many') else instance, *args, **kwargs)
