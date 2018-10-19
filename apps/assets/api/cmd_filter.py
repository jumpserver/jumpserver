# -*- coding: utf-8 -*-
#

from rest_framework_bulk import BulkModelViewSet
from django.shortcuts import get_object_or_404

from ..hands import IsOrgAdmin
from ..models import CommandFilter, CommandFilterRule
from .. import serializers


__all__ = ['CommandFilterViewSet', 'CommandFilterRuleViewSet']


class CommandFilterViewSet(BulkModelViewSet):
    permission_classes = (IsOrgAdmin,)
    queryset = CommandFilter.objects.all()
    serializer_class = serializers.CommandFilterSerializer


class CommandFilterRuleViewSet(BulkModelViewSet):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.CommandFilterRuleSerializer

    def get_queryset(self):
        fpk = self.kwargs.get('filter_pk')
        if not fpk:
            return CommandFilterRule.objects.none()
        cmd_filter = get_object_or_404(CommandFilter, pk=fpk)
        return cmd_filter.rules.all()


