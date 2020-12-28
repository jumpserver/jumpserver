# -*- coding: utf-8 -*-
#

from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed

from users.models import User
from common.mixins.api import CommonApiMixin
from common.permissions import IsValidUser, IsOrgAdmin
from common.exceptions import JMSException
from common.utils import lazyproperty
from common.const.http import POST, PUT
from orgs.utils import get_org_by_id
from .. import serializers
from ..permissions import IsAssignee, NotClosed
from ..models import Ticket
from .mixin import TicketMetaSerializerViewMixin


class TicketViewSet(TicketMetaSerializerViewMixin, CommonApiMixin, viewsets.ModelViewSet):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.TicketSerializer
    serializer_classes = {
        'default': serializers.TicketSerializer,
        'display': serializers.TicketDisplaySerializer,
        'apply': serializers.TicketApplySerializer,
        'approve': serializers.TicketApproveSerializer,
        'reject': serializers.TicketRejectSerializer,
        'close': serializers.TicketCloseSerializer,
    }
    filter_fields = [
        'id', 'title', 'type', 'action', 'status', 'applicant', 'applicant_display', 'processor',
        'processor_display', 'assignees__id'
    ]
    search_fields = [
        'title', 'action', 'type', 'status', 'applicant_display', 'processor_display'
    ]

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def reset_metadata_action(self):
        if self.action.lower() in ['metadata']:
            view_action = self.request.query_params.get('action') or 'apply'
            setattr(self, 'action', view_action)

    def get_serializer_class(self):
        self.reset_metadata_action()
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = Ticket.get_user_related_tickets(self.request.user)
        return queryset

    @action(detail=False, methods=[POST])
    def apply(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=[PUT], permission_classes=[IsOrgAdmin, IsAssignee, NotClosed])
    def approve(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=[PUT], permission_classes=[IsOrgAdmin, IsAssignee, NotClosed])
    def reject(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=[PUT], permission_classes=[IsOrgAdmin, IsAssignee, NotClosed])
    def close(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


class AssigneeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.AssigneeSerializer
    permission_classes = (IsValidUser,)
    filter_fields = ('id', 'name', 'username', 'email', 'source')
    search_fields = filter_fields

    def get_org(self):
        org_id = self.request.query_params.get('org_id')
        org = get_org_by_id(org_id)
        if not org:
            raise JMSException('The organization `{}` does not exist'.format(org_id))
        return org

    def get_queryset(self):
        org = self.get_org()
        queryset = User.get_super_and_org_admins(org=org)
        return queryset


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.CommentSerializer
    http_method_names = ['get', 'post']

    @lazyproperty
    def ticket(self):
        ticket_id = self.request.query_params.get('ticket_id')
        try:
            ticket = get_object_or_404(Ticket, pk=ticket_id)
            return ticket
        except Exception as e:
            raise JMSException(str(e))

    def check_permissions(self, request):
        ticket = self.ticket
        if request.user == ticket.applicant:
            return True
        if ticket.has_assignee(request.user):
            return True
        return False

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['ticket'] = self.ticket
        return context

    def get_queryset(self):
        queryset = self.ticket.comments.all()
        return queryset
