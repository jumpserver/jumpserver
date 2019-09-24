# -*- coding: utf-8 -*-
#
import re
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from common.fields import ChoiceDisplayField
from common.serializers import AdaptedBulkListSerializer
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
    serializer_choice_field = ChoiceDisplayField
    invalid_pattern = re.compile(r'[\.\*\+\[\\\?\{\}\^\$\|\(\)\#\<\>]')

    class Meta:
        model = CommandFilterRule
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
