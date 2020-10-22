# -*- coding: utf-8 -*-
#
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.translation import ugettext as _
from django.conf import settings

from assets.models import Asset, Node
from orgs.mixins.api import RootOrgViewMixin
from common.permissions import IsValidUser
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
        user = self.request.user

        q = Q(granted_by_permissions__system_users__id=system_user.id) & (
                Q(granted_by_permissions__users=user) |
                Q(granted_by_permissions__user_groups__users=user)
        )

        permed_assets = set()
        permed_assets.update(
            Asset.objects.filter(
                id__in=[a.id for a in assets]
            ).filter(q).distinct()
        )
        node_keys = Node.objects.filter(q).distinct().values_list('key', flat=True)

        nodes_assets_q = Q()
        for _key in node_keys:
            nodes_assets_q |= Q(nodes__key__startswith=f'{_key}:')
            nodes_assets_q |= Q(nodes__key=_key)

        permed_assets.update(
            Asset.objects.filter(
                id__in=[a.id for a in assets]
            ).filter(
                nodes_assets_q
            ).distinct()
        )

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
