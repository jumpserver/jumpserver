# -*- coding: utf-8 -*-
#

from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from django.shortcuts import get_object_or_404

from common.utils import reverse
from common.utils import lazyproperty
from orgs.mixins.api import OrgBulkModelViewSet
from tickets.api import GenericTicketStatusRetrieveCloseAPI
from ..hands import IsOrgAdmin, IsAppUser
from ..models import CommandFilter, CommandFilterRule
from .. import serializers


__all__ = [
    'CommandFilterViewSet', 'CommandFilterRuleViewSet', 'CommandConfirmAPI',
    'CommandConfirmStatusAPI'
]


class CommandFilterViewSet(OrgBulkModelViewSet):
    model = CommandFilter
    filterset_fields = ("name",)
    search_fields = filterset_fields
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.CommandFilterSerializer


class CommandFilterRuleViewSet(OrgBulkModelViewSet):
    model = CommandFilterRule
    filterset_fields = ("content",)
    search_fields = filterset_fields
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.CommandFilterRuleSerializer

    def get_queryset(self):
        fpk = self.kwargs.get('filter_pk')
        if not fpk:
            return CommandFilterRule.objects.none()
        cmd_filter = get_object_or_404(CommandFilter, pk=fpk)
        return cmd_filter.rules.all()


class CommandConfirmAPI(CreateAPIView):
    permission_classes = (IsAppUser, )
    serializer_class = serializers.CommandConfirmSerializer

    def create(self, request, *args, **kwargs):
        ticket = self.create_command_confirm_ticket()
        response_data = self.get_response_data(ticket)
        return Response(data=response_data, status=200)

    def create_command_confirm_ticket(self):
        ticket = self.serializer.cmd_filter_rule.create_command_confirm_ticket(
            run_command=self.serializer.data.get('run_command'),
            session=self.serializer.session,
            cmd_filter_rule=self.serializer.cmd_filter_rule,
            org_id=self.serializer.org.id
        )
        return ticket

    @staticmethod
    def get_response_data(ticket):
        confirm_status_url = reverse(
            view_name='api-assets:command-confirm-status',
            kwargs={'pk': str(ticket.id)}
        )
        ticket_detail_url = reverse(
            view_name='api-tickets:ticket-detail',
            kwargs={'pk': str(ticket.id)},
            external=True, api_to_ui=True
        )
        ticket_detail_url = '{url}?type={type}'.format(url=ticket_detail_url, type=ticket.type)
        return {
            'check_confirm_status': {'method': 'GET', 'url': confirm_status_url},
            'close_confirm': {'method': 'DELETE', 'url': confirm_status_url},
            'ticket_detail_url': ticket_detail_url,
            'reviewers': [str(user) for user in ticket.assignees.all()]
        }

    @lazyproperty
    def serializer(self):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer


class CommandConfirmStatusAPI(GenericTicketStatusRetrieveCloseAPI):
    pass

