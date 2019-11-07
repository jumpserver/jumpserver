# -*- coding: utf-8 -*-
#
from rest_framework import viewsets, generics
from django.shortcuts import get_object_or_404

from common.permissions import IsValidUser
from common.mixins import CommonApiMixin
from .. import serializers
from ..models import LoginConfirmTicket


class LoginConfirmTicketViewSet(CommonApiMixin, viewsets.ModelViewSet):
    serializer_class = serializers.LoginConfirmTicketSerializer
    permission_classes = (IsValidUser,)
    filter_fields = ['status', 'title']
    search_fields = ['user_display', 'title', 'ip', 'city']

    def get_queryset(self):
        queryset = LoginConfirmTicket.objects.all()\
            .filter(assignees=self.request.user)
        return queryset


class LoginConfirmTicketsCreateActionApi(generics.CreateAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.LoginConfirmTicketActionSerializer

    def get_ticket(self):
        ticket_id = self.kwargs.get('pk')
        queryset = LoginConfirmTicket.objects.all()\
            .filter(assignees=self.request.user)
        ticket = get_object_or_404(queryset, id=ticket_id)
        return ticket

    def get_serializer_context(self):
        context = super().get_serializer_context()
        ticket = self.get_ticket()
        context['ticket'] = ticket
        return context
