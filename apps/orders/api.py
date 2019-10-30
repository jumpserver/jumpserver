# -*- coding: utf-8 -*-
#
from rest_framework import viewsets, generics
from django.shortcuts import get_object_or_404

from common.permissions import IsValidUser
from common.mixins import CommonApiMixin
from . import serializers
from .models import LoginConfirmOrder


class LoginConfirmOrderViewSet(CommonApiMixin, viewsets.ModelViewSet):
    serializer_class = serializers.LoginConfirmOrderSerializer
    permission_classes = (IsValidUser,)
    filter_fields = ['status', 'title']
    search_fields = ['user_display', 'title', 'ip', 'city']

    def get_queryset(self):
        queryset = LoginConfirmOrder.objects.all()\
            .filter(assignees=self.request.user)
        return queryset


class LoginConfirmOrderCreateActionApi(generics.CreateAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.LoginConfirmOrderActionSerializer

    def get_order(self):
        order_id = self.kwargs.get('pk')
        queryset = LoginConfirmOrder.objects.all()\
            .filter(assignees=self.request.user)
        order = get_object_or_404(queryset, id=order_id)
        return order

    def get_serializer_context(self):
        context = super().get_serializer_context()
        order = self.get_order()
        context['order'] = order
        return context
