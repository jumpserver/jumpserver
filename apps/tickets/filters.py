from django.db.models import Exists, F, OuterRef, Q, Value
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from common.drf.filters import BaseFilterSet
from orgs.models import Organization
from tickets.models import (
    Ticket, ApplyAssetTicket,
    ApplyLoginTicket, ApplyLoginAssetTicket, ApplyCommandTicket,
    TicketAssignee,
)


class TicketFilter(BaseFilterSet):
    applicant = filters.UUIDFilter(
        field_name='applicant_id', label=_('Applicant ID')
    )
    assignees__id = filters.UUIDFilter(
        method='filter_assignees_id', label=_('Assignee ID')
    )
    relevant_asset = filters.CharFilter(
        method='filter_relevant_asset',
        label=_('Relevant asset name or address')
    )
    relevant_command = filters.CharFilter(
        method='filter_relevant_command', label=_('Relevant command')
    )
    applicant_username_name = filters.CharFilter(
        method='filter_applicant_username_name',
        label=_('Applicant name or username')
    )
    state = filters.CharFilter(
        method='filter_state', label=_('Approval result')
    )
    status = filters.CharFilter(
        field_name='status', label=_('Ticket status')
    )
    org_name = filters.CharFilter(
        method='filter_org_name', label=_('Organization name')
    )

    class Meta:
        model = Ticket
        fields = (
            'id', 'title', 'serial_num', 'type', 'state', 'status',
            'applicant', 'applicant_username_name', 'assignees__id',
            'relevant_asset', 'relevant_command', 'org_name', 'org_id',
        )
        fields_operator = {
            'assignees__id': ('exact',),
            'org_id': ('exact', 'in'),
            'state': ('exact',),
            'status': ('exact',),
            'relevant_asset': ('icontains',),
            'relevant_command': ('icontains',),
            'applicant_username_name': ('icontains',),
            'org_name': ('icontains',),
        }

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
        current_assignee_tickets = TicketAssignee.objects.filter(
            step__ticket_id=OuterRef('pk'),
            step__level=OuterRef('approval_step'),
            assignee_id=value,
        )
        return queryset.filter(Exists(current_assignee_tickets))

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


class ApplyAssetTicketFilter(TicketFilter):
    class Meta(TicketFilter.Meta):
        model = ApplyAssetTicket


class ApplyLoginTicketFilter(TicketFilter):
    class Meta(TicketFilter.Meta):
        model = ApplyLoginTicket


class ApplyLoginAssetTicketFilter(TicketFilter):
    class Meta(TicketFilter.Meta):
        model = ApplyLoginAssetTicket


class ApplyCommandTicketFilter(TicketFilter):
    class Meta(TicketFilter.Meta):
        model = ApplyCommandTicket
