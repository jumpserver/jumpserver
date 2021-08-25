from django_filters import rest_framework as filters
from common.drf.filters import BaseFilterSet

from tickets.models import Ticket


class TicketFilter(BaseFilterSet):
    assignees__id = filters.UUIDFilter(method='filter_assignees_id')

    class Meta:
        model = Ticket
        fields = (
            'id', 'title', 'type', 'status', 'applicant', 'assignees__id',
            'applicant_display',
        )

    def filter_assignees_id(self, queryset, name, value):
        return queryset.filter(ticket_steps__ticket_assignees__assignee__id=value)
