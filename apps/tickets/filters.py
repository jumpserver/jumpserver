from django_filters import rest_framework as filters
from django.db.models import Subquery, OuterRef

from common.drf.filters import BaseFilterSet

from tickets.models import (
    Ticket, TicketStep, ApplyAssetTicket, ApplyApplicationTicket,
    ApplyLoginTicket, ApplyLoginAssetTicket, ApplyCommandTicket
)


class TicketFilter(BaseFilterSet):
    assignees__id = filters.UUIDFilter(method='filter_assignees_id')

    class Meta:
        model = Ticket
        fields = (
            'id', 'title', 'type', 'status', 'state', 'applicant', 'assignees__id'
        )

    def filter_assignees_id(self, queryset, name, value):
        step_qs = TicketStep.objects.filter(
            level=OuterRef("approval_step")
        ).values_list('id', flat=True)
        return queryset.filter(
            ticket_steps__id__in=Subquery(step_qs),
            ticket_steps__ticket_assignees__assignee__id=value
        )


class ApplyAssetTicketFilter(BaseFilterSet):
    class Meta:
        model = ApplyAssetTicket
        fields = ('id',)


class ApplyApplicationTicketFilter(BaseFilterSet):
    class Meta:
        model = ApplyApplicationTicket
        fields = ('id',)


class ApplyLoginTicketFilter(BaseFilterSet):
    class Meta:
        model = ApplyLoginTicket
        fields = ('id',)


class ApplyLoginAssetTicketFilter(BaseFilterSet):
    class Meta:
        model = ApplyLoginAssetTicket
        fields = ('id',)


class ApplyCommandTicketFilter(BaseFilterSet):
    class Meta:
        model = ApplyCommandTicket
        fields = ('id',)
