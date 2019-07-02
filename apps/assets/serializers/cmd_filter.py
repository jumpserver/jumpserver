# -*- coding: utf-8 -*-
#
import re
from rest_framework import serializers

from common.fields import ChoiceDisplayField
from common.serializers import AdaptedBulkListSerializer
from ..models import CommandFilter, CommandFilterRule, SystemUser
from orgs.mixins import BulkOrgResourceModelSerializer


class CommandFilterSerializer(BulkOrgResourceModelSerializer):
    rules = serializers.PrimaryKeyRelatedField(queryset=CommandFilterRule.objects.all(), many=True)
    system_users = serializers.PrimaryKeyRelatedField(queryset=SystemUser.objects.all(), many=True)

    class Meta:
        model = CommandFilter
        list_serializer_class = AdaptedBulkListSerializer
        fields = '__all__'


class CommandFilterRuleSerializer(BulkOrgResourceModelSerializer):
    serializer_choice_field = ChoiceDisplayField
    invalid_pattern = re.compile(r'[\.\*\+\[\\\?\{\}\^\$\|\(\)\#\<\>]')

    class Meta:
        model = CommandFilterRule
        fields = '__all__'
        list_serializer_class = AdaptedBulkListSerializer

    def validate_content(self, content):
        if self.invalid_pattern.search(content):
            invalid_char = self.invalid_pattern.pattern.replace('\\', '')
            msg = _("Content should not be contain: {}").format(invalid_char)
            raise serializers.ValidationError(msg)
        return content
