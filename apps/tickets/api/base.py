# -*- coding: utf-8 -*-
#
from rest_framework import viewsets, generics

from .. import serializers, models


class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.TicketSerializer

    def get_queryset(self):
        queryset = models.Ticket.objects.all().none()
        return queryset


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.CommentSerializer

    def get_queryset(self):
        queryset = models.Comment.objects.none()
        return queryset
