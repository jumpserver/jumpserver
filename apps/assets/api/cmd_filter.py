# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404

from orgs.mixins.api import OrgBulkModelViewSet
from ..hands import IsOrgAdmin
from ..models import CommandFilter, CommandFilterRule
from .. import serializers


__all__ = ['CommandFilterViewSet', 'CommandFilterRuleViewSet']


class CommandFilterViewSet(OrgBulkModelViewSet):
    model = CommandFilter
    filter_fields = ("name",)
    search_fields = filter_fields
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.CommandFilterSerializer


class CommandFilterRuleViewSet(OrgBulkModelViewSet):
    model = CommandFilterRule
    filter_fields = ("content",)
    search_fields = filter_fields
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.CommandFilterRuleSerializer

    def get_queryset(self):
        fpk = self.kwargs.get('filter_pk')
        if not fpk:
            return CommandFilterRule.objects.none()
        cmd_filter = get_object_or_404(CommandFilter, pk=fpk)
        return cmd_filter.rules.all()


