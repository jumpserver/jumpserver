# -*- coding: utf-8 -*-
#

from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed

from common.permissions import IsValidUser, IsOrgAdmin
from common.utils import lazyproperty
from common.const.http import POST, PATCH
from .. import serializers
from ..permissions import IsAssignee, NotClosed
from ..models import Ticket
from . import mixin


class TicketViewSet(mixin.TicketMetaSerializerViewMixin, viewsets.ModelViewSet):
    permission_classes = (IsValidUser,)
    queryset = Ticket.objects.all()
    serializer_class = serializers.TicketSerializer
    filter_fields = ['status', 'type', 'title', 'action', 'applicant_display']
    search_fields = ['applicant_display', 'title']

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    @action(detail=False, methods=[POST])
    def apply(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=[PATCH], permission_classes=[IsOrgAdmin, IsAssignee, NotClosed])
    def approve(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=[PATCH], permission_classes=[IsOrgAdmin, IsAssignee, NotClosed])
    def reject(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=[PATCH], permission_classes=[IsOrgAdmin, IsAssignee, NotClosed])
    def close(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


class TicketCommentViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.CommentSerializer
    http_method_names = ['get', 'post']

    def check_permissions(self, request):
        ticket = self.ticket
        if request.user == ticket.user or \
                request.user in ticket.assignees.all():
            return True
        return False

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['ticket'] = self.ticket
        return context

    @lazyproperty
    def ticket(self):
        ticket_id = self.kwargs.get('ticket_id')
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        return ticket

    def get_queryset(self):
        queryset = self.ticket.comments.all()
        return queryset
