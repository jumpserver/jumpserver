# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.drf.fields import LabeledChoiceField
from terminal.models import Session
from . import models
from .const import (
    ActionChoices, OperateChoices, MFAChoices, LoginStatusChoices, LoginTypeChoices
)


class FTPLogSerializer(serializers.ModelSerializer):
    operate = LabeledChoiceField(choices=OperateChoices.choices, label=_('Operate'))

    class Meta:
        model = models.FTPLog
        fields_mini = ['id']
        fields_small = fields_mini + [
            'user', 'remote_addr', 'asset', 'system_user', 'org_id',
            'operate', 'filename', 'is_success', 'date_start',
        ]
        fields = fields_small


class UserLoginLogSerializer(serializers.ModelSerializer):
    mfa = LabeledChoiceField(choices=MFAChoices.choices, label=_('MFA'))
    type = LabeledChoiceField(choices=LoginTypeChoices.choices, label=_('Type'))
    status = LabeledChoiceField(choices=LoginStatusChoices.choices, label=_('Status'))

    class Meta:
        model = models.UserLoginLog
        fields_mini = ['id']
        fields_small = fields_mini + [
            'username', 'type', 'ip', 'city', 'user_agent',
            'mfa', 'reason', 'reason_display', 'backend',
            'backend_display', 'status', 'datetime',
        ]
        fields = fields_small
        extra_kwargs = {
            "user_agent": {'label': _('User agent')},
            "reason_display": {'label': _('Reason display')},
            'backend_display': {'label': _('Authentication backend')}
        }


class OperateLogSerializer(serializers.ModelSerializer):
    action = LabeledChoiceField(choices=ActionChoices.choices, label=_('Action'))

    class Meta:
        model = models.OperateLog
        fields_mini = ['id']
        fields_small = fields_mini + [
            'user', 'action', 'resource_type', 'resource_type_display',
            'resource', 'remote_addr', 'datetime', 'org_id'
        ]
        fields = fields_small
        extra_kwargs = {
            'resource_type_display': {'label': _('Resource Type')}
        }


class PasswordChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PasswordChangeLog
        fields = (
            'id', 'user', 'change_by', 'remote_addr', 'datetime'
        )


class SessionAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = '__all__'

#
# class CommandExecutionSerializer(serializers.ModelSerializer):
#     is_success = serializers.BooleanField(read_only=True, label=_('Is success'))
#     hosts_display = serializers.ListSerializer(
#         child=serializers.CharField(), source='hosts', read_only=True, label=_('Hosts display')
#     )
#
#     class Meta:
#         model = CommandExecution
#         fields_mini = ['id']
#         fields_small = fields_mini + [
#             'command', 'is_finished', 'user',
#             'date_start', 'result', 'is_success', 'org_id'
#         ]
#         fields = fields_small + ['hosts', 'hosts_display', 'user_display']
#         extra_kwargs = {
#             'result': {'label': _('Result')},  # model 上的方法，只能在这修改
#             'is_success': {'label': _('Is success')},
#             'hosts': {'label': _('Hosts')},  # 外键，会生成 sql。不在 model 上修改
#             'user': {'label': _('User')},
#             'user_display': {'label': _('User display')},
#         }
#
#     @classmethod
#     def setup_eager_loading(cls, queryset):
#         """ Perform necessary eager loading of data. """
#         queryset = queryset.prefetch_related('user', 'hosts')
#         return queryset
#
#
# class CommandExecutionHostsRelationSerializer(BulkSerializerMixin, serializers.ModelSerializer):
#     asset_display = serializers.ReadOnlyField()
#     commandexecution_display = serializers.ReadOnlyField()
#
#     class Meta:
#         model = CommandExecution.hosts.through
#         fields = [
#             'id', 'asset', 'asset_display', 'commandexecution', 'commandexecution_display'
#         ]
