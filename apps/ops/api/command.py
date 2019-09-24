# -*- coding: utf-8 -*-
#
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import ugettext as _
from django.conf import settings

from orgs.mixins.api import RootOrgViewMixin
from common.permissions import IsValidUser
from perms.utils import AssetPermissionUtilV2
from ..models import CommandExecution
from ..serializers import CommandExecutionSerializer
from ..tasks import run_command_execution


class CommandExecutionViewSet(RootOrgViewMixin, viewsets.ModelViewSet):
    serializer_class = CommandExecutionSerializer
    permission_classes = (IsValidUser,)

    def get_queryset(self):
        return CommandExecution.objects.filter(
            user_id=str(self.request.user.id)
        )

    def check_hosts(self, serializer):
        data = serializer.validated_data
        assets = data["hosts"]
        system_user = data["run_as"]
        util = AssetPermissionUtilV2(self.request.user)
        util.filter_permissions(system_users=system_user.id)
        permed_assets = util.get_assets().filter(id__in=[a.id for a in assets])
        invalid_assets = set(assets) - set(permed_assets)
        if invalid_assets:
            msg = _("Not has host {} permission").format(
                [str(a.id) for a in invalid_assets]
            )
            raise ValidationError({"hosts": msg})

    def check_permissions(self, request):
        if not settings.SECURITY_COMMAND_EXECUTION and request.user.is_common_user:
            return self.permission_denied(request, "Command execution disabled")
        return super().check_permissions(request)

    def perform_create(self, serializer):
        self.check_hosts(serializer)
        instance = serializer.save()
        instance.user = self.request.user
        instance.save()
        cols = self.request.query_params.get("cols", '80')
        rows = self.request.query_params.get("rows", '24')
        transaction.on_commit(lambda: run_command_execution.apply_async(
            args=(instance.id,), kwargs={"cols": cols, "rows": rows},
            task_id=str(instance.id)
        ))
