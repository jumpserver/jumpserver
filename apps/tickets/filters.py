from django.db.models import Value, F, Q
from django.db.models.functions import Concat
from django_filters import rest_framework as filters

from common.drf.filters import BaseFilterSet
from tickets.models import (
    Ticket, ApplyAssetTicket,
    ApplyLoginTicket, ApplyLoginAssetTicket, ApplyCommandTicket
)


class TicketFilter(BaseFilterSet):
    assignees__id = filters.UUIDFilter(method='filter_assignees_id')
    relevant_asset = filters.CharFilter(method='filter_relevant_asset')
    relevant_command = filters.CharFilter(method='filter_relevant_command')
    applicant_username_name = filters.CharFilter(method='filter_applicant_username_name')

    class Meta:
        model = Ticket
        fields = (
            'id', 'title', 'type', 'status', 'state', 'applicant', 'assignees__id'
        )

    def filter_assignees_id(self, queryset, name, value):
        return queryset.filter(
            ticket_steps__ticket_assignees__assignee__id=value
        )

    def filter_relevant_asset(self, queryset, name, value):
        asset_ids = ApplyAssetTicket.objects.annotate(
            asset_str=Concat(
                F('apply_assets__name'), Value('('),
                F('apply_assets__address'), Value(')')
            )
        ).filter(
            asset_str__icontains=value
        ).values_list('id', flat=True)

        login_asset_ids = ApplyLoginAssetTicket.objects.annotate(
            asset_str=Concat(
                F('apply_login_asset__name'), Value('('),
                F('apply_login_asset__address'), Value(')')
            )
        ).filter(
            asset_str__icontains=value
        ).values_list('id', flat=True)

        command_ids = ApplyCommandTicket.objects.filter(
            apply_run_asset__icontains=value
        ).values_list('id', flat=True)

        ticket_ids = list(set(list(asset_ids) + list(login_asset_ids) + list(command_ids)))
        return queryset.filter(id__in=ticket_ids)

    def filter_relevant_command(self, queryset, name, value):
        command_ids = ApplyCommandTicket.objects.filter(
            apply_run_command__icontains=value
        ).values_list('id', flat=True)
        return queryset.filter(id__in=list(command_ids))

    def filter_applicant_username_name(self, queryset, name, value):
        return queryset.filter(
            Q(applicant__name__icontains=value) |
            Q(applicant__username__icontains=value)
        )


class ApplyAssetTicketFilter(BaseFilterSet):
    class Meta:
        model = ApplyAssetTicket
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
