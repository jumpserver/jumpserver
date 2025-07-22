from django.db.models import Value, F, Q
from django.db.models.functions import Concat
from django_filters import rest_framework as filters

from common.drf.filters import BaseFilterSet
from orgs.models import Organization
from tickets.models import (
    Ticket, ApplyAssetTicket,
    ApplyLoginTicket, ApplyLoginAssetTicket, ApplyCommandTicket
)


class TicketFilter(BaseFilterSet):
    assignees__id = filters.UUIDFilter(method='filter_assignees_id')
    relevant_asset = filters.CharFilter(method='filter_relevant_asset')
    relevant_command = filters.CharFilter(method='filter_relevant_command')
    applicant_username_name = filters.CharFilter(method='filter_applicant_username_name')
    state = filters.CharFilter(method='filter_state')
    org_name = filters.CharFilter(method='filter_org_name', label='Organization Name')

    class Meta:
        model = Ticket
        fields = (
            'id', 'title', 'type', 'status', 'state',
            'applicant', 'assignees__id', 'org_name', 'org_id'
        )

    @staticmethod
    def filter_org_name(queryset, name, value):
        matched_org_ids = Organization.objects.filter(
            name__icontains=value
        ).values_list('id', flat=True)

        matched_org_ids = [str(_id) for _id in matched_org_ids]
        if not matched_org_ids:
            return queryset.none()

        return queryset.filter(org_id__in=matched_org_ids)

    @staticmethod
    def filter_assignees_id(queryset, name, value):
        return queryset.filter(
            ticket_steps__level=F('approval_step'),
            ticket_steps__ticket_assignees__assignee_id=value
        )

    @staticmethod
    def filter_relevant_asset(queryset, name, value):
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

    @staticmethod
    def filter_relevant_command(queryset, name, value):
        command_ids = ApplyCommandTicket.objects.filter(
            apply_run_command__icontains=value
        ).values_list('id', flat=True)
        return queryset.filter(id__in=list(command_ids))

    @staticmethod
    def filter_applicant_username_name(queryset, name, value):
        return queryset.filter(
            Q(applicant__name__icontains=value) |
            Q(applicant__username__icontains=value)
        )

    @staticmethod
    def filter_state(queryset, name, value):
        if value == 'all':
            return queryset
        return queryset.filter(state=value)


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
