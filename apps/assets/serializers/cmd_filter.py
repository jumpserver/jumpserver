# -*- coding: utf-8 -*-
#
import re
from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _
from ..models import CommandFilter, CommandFilterRule
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from orgs.utils import tmp_to_root_org
from common.utils import get_object_or_none, lazyproperty
from terminal.models import Session


class CommandFilterSerializer(BulkOrgResourceModelSerializer):
    class Meta:
        model = CommandFilter
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'org_id', 'org_name', 'is_active',
            'date_created', 'date_updated',
            'comment', 'created_by',
        ]
        fields_fk = ['rules']
        fields_m2m = ['users', 'user_groups', 'system_users', 'nodes', 'assets', 'applications']
        fields = fields_small + fields_fk + fields_m2m
        extra_kwargs = {
            'rules': {'read_only': True},
            'date_created': {'label': _("Date created")},
            'date_updated': {'label': _("Date updated")},
        }


class CommandFilterRuleSerializer(BulkOrgResourceModelSerializer):
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_("Type display"))
    action_display = serializers.ReadOnlyField(source='get_action_display', label=_("Action display"))

    class Meta:
        model = CommandFilterRule
        fields_mini = ['id']
        fields_small = fields_mini + [
            'type', 'type_display', 'content', 'ignore_case', 'pattern',
            'priority', 'action', 'action_display', 'reviewers',
            'date_created', 'date_updated', 'comment', 'created_by',
        ]
        fields_fk = ['filter']
        fields = fields_small + fields_fk
        extra_kwargs = {
            'date_created': {'label': _("Date created")},
            'date_updated': {'label': _("Date updated")},
            'action_display': {'label': _("Action display")},
            'pattern': {'label': _("Pattern")}
        }

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

    def validate_content(self, content):
        tp = self.initial_data.get("type")
        if tp == CommandFilterRule.TYPE_COMMAND:
            regex = CommandFilterRule.construct_command_regex(content)
        else:
            regex = content
        ignore_case = self.initial_data.get('ignore_case')
        succeed, error, pattern = CommandFilterRule.compile_regex(regex, ignore_case)
        if not succeed:
            raise serializers.ValidationError(error)
        return content


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
