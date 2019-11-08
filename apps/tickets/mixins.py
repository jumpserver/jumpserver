# -*- coding: utf-8 -*-
#
from django.db.models import Q


class TicketMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        assign = self.request.GET.get('assign', None)
        if assign is None:
            queryset = queryset.filter(
                Q(assignees=self.request.user) | Q(user=self.request.user)
            ).distinct()
        elif assign in ['1']:
            queryset = queryset.filter(assignees=self.request.user)
        else:
            queryset = queryset.filter(user=self.request.user)
        return queryset
