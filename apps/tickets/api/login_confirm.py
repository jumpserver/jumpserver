# -*- coding: utf-8 -*-
#
from rest_framework import viewsets, generics
from rest_framework.serializers import ValidationError
from django.shortcuts import get_object_or_404

from common.permissions import IsValidUser
from common.mixins import CommonApiMixin
from .. import serializers, mixins
from ..models import LoginConfirmTicket


class LoginConfirmTicketViewSet(CommonApiMixin, mixins.TicketMixin, viewsets.ModelViewSet):
    serializer_class = serializers.LoginConfirmTicketSerializer
    permission_classes = (IsValidUser,)
    queryset = LoginConfirmTicket.objects.all()
    filter_fields = ['status', 'title', 'action', 'ip']
    search_fields = ['user_display', 'title', 'ip', 'city']

    # def check_update_permission(self, serializer):
    #     data = serializer.validated_data
    #     action = data.get("action")
    #     user = self.request.user
    #     instance = serializer.instance
    #     if action and user not in instance.assignees.all():
    #         error = {"action": "Only assignees can update"}
    #         raise ValidationError(error)
    #
    # def perform_update(self, serializer):
    #     self.check_update_permission(serializer)
