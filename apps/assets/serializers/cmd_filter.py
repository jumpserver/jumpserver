# -*- coding: utf-8 -*-
#
import re
from rest_framework import serializers

from common.drf.serializers import AdaptedBulkListSerializer
from ..models import CommandFilter, CommandFilterRule
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from orgs.utils import tmp_to_root_org
from common.utils import get_object_or_none, lazyproperty
from terminal.models import Session


class CommandFilterSerializer(BulkOrgResourceModelSerializer):

    class Meta:
        model = CommandFilter
        list_serializer_class = AdaptedBulkListSerializer
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'org_id', 'org_name',
            'is_active',
            'date_created', 'date_updated',
            'comment', 'created_by',
        ]
        fields_fk = ['rules']
        fields_m2m = ['system_users']
        fields = fields_small + fields_fk + fields_m2m
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
           'date_created', 'date_updated',
           'comment', 'created_by',
        ]
        fields_fk = ['filter']
        fields = '__all__'
        list_serializer_class = AdaptedBulkListSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_action_choices()

    def set_action_choices(self):
        from django.conf import settings
        action = self.fields.get('action')
        if not action:
            return
        choices = action._choices
        if not settings.XPACK_ENABLED:
            choices.pop(CommandFilterRule.ActionChoices.confirm, None)
        action._choices = choices

    # def validate_content(self, content):
    #     tp = self.initial_data.get("type")
    #     if tp == CommandFilterRule.TYPE_REGEX:
    #         return content
    #     if self.invalid_pattern.search(content):
    #         invalid_char = self.invalid_pattern.pattern.replace('\\', '')
    #         msg = _("Content should not be contain: {}").format(invalid_char)
    #         raise serializers.ValidationError(msg)
    #     return content


class CommandConfirmSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=True, allow_null=False)
    cmd_filter_rule_id = serializers.UUIDField(required=True, allow_null=False)
    run_command = serializers.CharField(required=True, allow_null=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None
        self.cmd_filter_rule = None

    def validate_session_id(self, session_id):
        self.session = self.validate_object_exist(Session, session_id)
        return session_id

    def validate_cmd_filter_rule_id(self, cmd_filter_rule_id):
        self.cmd_filter_rule = self.validate_object_exist(CommandFilterRule, cmd_filter_rule_id)
        return cmd_filter_rule_id

    @staticmethod
    def validate_object_exist(model, field_id):
        with tmp_to_root_org():
            obj = get_object_or_none(model, id=field_id)
        if not obj:
            error = '{} Model object does not exist'.format(model.__name__)
            raise serializers.ValidationError(error)
        return obj

    @lazyproperty
    def org(self):
        return self.session.org
