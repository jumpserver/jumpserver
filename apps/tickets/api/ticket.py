# -*- coding: utf-8 -*-
#

from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed

from users.models import User
from common.mixins.api import CommonApiMixin
from common.permissions import IsValidUser, IsOrgAdmin
from common.exceptions import JMSException
from common.utils import lazyproperty
from common.const.http import POST, PUT
from .. import serializers
from ..permissions import IsAssignee, NotClosed
from ..models import Ticket
from . import mixin


class TicketViewSet(mixin.TicketMetaSerializerViewMixin, CommonApiMixin, viewsets.ModelViewSet):
    permission_classes = (IsValidUser,)
    queryset = Ticket.objects.all()
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
        'type', 'title', 'action', 'status', 'applicant', 'processor', 'assignees__id'
    ]
    search_fields = ['title', 'applicant_display']

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def reset_action_name_for_metadata(self):
        if self.action.lower() in ['metadata']:
            view_action = self.request.query_params.get('action') or 'apply'
            setattr(self, 'action', view_action)

    def get_serializer_class(self):
        self.reset_action_name_for_metadata()
        return super().get_serializer_class()

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

    def get_queryset(self):
        # 携带查询参数?oid=org_id
        queryset = User.get_super_and_org_admins()
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
