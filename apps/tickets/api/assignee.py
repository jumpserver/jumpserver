# -*- coding: utf-8 -*-
#
from rest_framework import viewsets

from common.permissions import IsValidUser
from users.models import User
from .. import serializers


class AssigneeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.AssigneeSerializer
    filterset_fields = ('id', 'name', 'username', 'email', 'source')
    search_fields = filterset_fields

    def get_queryset(self):
        queryset = User.get_auditor_and_users()
        return queryset
