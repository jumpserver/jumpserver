# -*- coding: utf-8 -*-
#

from rest_framework import viewsets, mixins
from django.shortcuts import get_object_or_404
from common.exceptions import JMSException
from common.utils import lazyproperty
from tickets import serializers
from tickets.models import Ticket
from tickets.permissions.comment import IsAssignee, IsApplicant, IsSwagger


__all__ = ['CommentViewSet']


class CommentViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.CommentSerializer
    permission_classes = (IsAssignee | IsApplicant | IsSwagger,)

    @lazyproperty
    def ticket(self):
        if getattr(self, 'swagger_fake_view', False):
            return Ticket()
        ticket_id = self.request.query_params.get('ticket_id')
        try:
            ticket = get_object_or_404(Ticket, pk=ticket_id)
            return ticket
        except Exception as e:
            raise JMSException(str(e))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['ticket'] = self.ticket
        return context

    def get_queryset(self):
        queryset = self.ticket.comments.all()
        return queryset
