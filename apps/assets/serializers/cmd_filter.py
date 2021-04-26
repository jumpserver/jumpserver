# -*- coding: utf-8 -*-
#
import re
from rest_framework import serializers

from common.drf.serializers import AdaptedBulkListSerializer
from ..models import CommandFilter, CommandFilterRule, SystemUser
from orgs.mixins.serializers import BulkOrgResourceModelSerializer


class CommandFilterSerializer(BulkOrgResourceModelSerializer):

    class Meta:
        model = CommandFilter
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'org_id', 'org_name', 'is_active', 'comment',
            'created_by', 'date_created', 'date_updated', 'rules', 'system_users'
        ]

        extra_kwargs = {
            'rules': {'read_only': True},
            'system_users': {'required': False},
        }


class CommandFilterRuleSerializer(BulkOrgResourceModelSerializer):
    invalid_pattern = re.compile(r'[\.\*\+\[\\\?\{\}\^\$\|\(\)\#\<\>]')
    type_display = serializers.ReadOnlyField(source='get_type_display')
    action_display = serializers.ReadOnlyField(source='get_action_display')

    class Meta:
        model = CommandFilterRule
        fields_mini = ['id']
        fields_small = fields_mini + [
           'type', 'type_display', 'content', 'priority',
           'action', 'action_display', 'reviewers',
           'comment', 'created_by', 'date_created', 'date_updated'
        ]
        fields_fk = ['filter']
        fields = '__all__'
        list_serializer_class = AdaptedBulkListSerializer

    # def validate_content(self, content):
    #     tp = self.initial_data.get("type")
    #     if tp == CommandFilterRule.TYPE_REGEX:
    #         return content
    #     if self.invalid_pattern.search(content):
    #         invalid_char = self.invalid_pattern.pattern.replace('\\', '')
    #         msg = _("Content should not be contain: {}").format(invalid_char)
    #         raise serializers.ValidationError(msg)
    #     return content
