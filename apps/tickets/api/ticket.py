# -*- coding: utf-8 -*-
#

from rest_framework import viewsets
from django.shortcuts import get_object_or_404

from common.permissions import IsValidUser
from common.utils import lazyproperty
from .. import serializers, models, mixins


class TicketViewSet(mixins.TicketMixin, viewsets.ModelViewSet):
    serializer_class = serializers.TicketSerializer
    queryset = models.Ticket.objects.all()
    permission_classes = (IsValidUser,)
    filter_fields = ['status', 'title', 'action']
    search_fields = ['user_display', 'title']


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
