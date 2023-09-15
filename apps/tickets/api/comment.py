# -*- coding: utf-8 -*-
#
from rest_framework import viewsets, mixins

from common.exceptions import JMSException
from common.utils import lazyproperty
from rbac.permissions import RBACPermission
from tickets import serializers
from tickets.models import Ticket, Comment
from tickets.permissions.comment import IsAssignee, IsApplicant, IsSwagger

__all__ = ['CommentViewSet']


class CommentViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.CommentSerializer
    permission_classes = (RBACPermission, IsSwagger | IsAssignee | IsApplicant)
    rbac_perms = {
        '*': 'tickets.view_ticket'
    }

    @lazyproperty
    def ticket(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        ticket_id = self.request.query_params.get('ticket_id')
        ticket = Ticket.all().filter(pk=ticket_id).first()
        if not ticket:
            raise JMSException('Not found Ticket object about `id={}`'.format(ticket_id))
        return ticket

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['ticket'] = self.ticket
        return context

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Comment.objects.none()
        queryset = self.ticket.comments.all()
        return queryset
