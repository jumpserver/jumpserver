# -*- coding: utf-8 -*-
#
from rest_framework import viewsets
from django.db import transaction
from django.conf import settings

from common.permissions import IsValidUser
from ..models import CommandExecution
from ..serializers import CommandExecutionSerializer
from ..tasks import run_command_execution


class CommandExecutionViewSet(viewsets.ModelViewSet):
    serializer_class = CommandExecutionSerializer
    permission_classes = (IsValidUser,)

    def get_queryset(self):
        return CommandExecution.objects.filter(
            user_id=str(self.request.user.id)
        )

    def check_permissions(self, request):
        if not settings.SECURITY_COMMAND_EXECUTION:
            return self.permission_denied(request, "Command execution disabled")
        return super().check_permissions(request)

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.user = self.request.user
        instance.save()
        transaction.on_commit(lambda: run_command_execution.apply_async(
            args=(instance.id,), task_id=str(instance.id)
        ))
