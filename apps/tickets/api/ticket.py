# -*- coding: utf-8 -*-
#

from rest_framework import viewsets
from django.shortcuts import get_object_or_404

from common.permissions import IsValidUser
from common.utils import lazyproperty
from .. import serializers, models
from . import mixin


class TicketViewSet(mixin.TicketMetaSerializerViewMixin, viewsets.ModelViewSet):
    permission_classes = (IsValidUser,)
    queryset = models.Ticket.objects.all()
    serializer_class = serializers.TicketSerializer
    filter_fields = ['status', 'type', 'title', 'action', 'applicant_display']
    search_fields = ['applicant_display', 'title']

    def approve(self):
        pass

    def reject(self):
        pass

    def close(self):
        pass


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
        ticket = get_object_or_404(models.Ticket, pk=ticket_id)
        return ticket

    def get_queryset(self):
        queryset = self.ticket.comments.all()
        return queryset
