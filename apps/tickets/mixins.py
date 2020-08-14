# -*- coding: utf-8 -*-
#
from django.db.models import Q
from .models import Ticket


class TicketMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        assign = self.request.GET.get('assign', None)
        if assign is None:
            queryset = Ticket.get_related_tickets(self.request.user, queryset)
        elif assign in ['1']:
            queryset = Ticket.get_assigned_tickets(self.request.user, queryset)
        else:
            queryset = Ticket.get_my_tickets(self.request.user, queryset)
        return queryset
