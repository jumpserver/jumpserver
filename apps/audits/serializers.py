# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from django.db.models import F

from common.mixins import BulkSerializerMixin
from terminal.models import Session
from ops.models import CommandExecution
from . import models


class FTPLogSerializer(serializers.ModelSerializer):
    operate_display = serializers.ReadOnlyField(source='get_operate_display', label=_('Operate display'))

    class Meta:
        model = models.FTPLog
        fields_mini = ['id']
        fields_small = fields_mini + [
            'user', 'remote_addr', 'asset', 'system_user', 'org_id',
            'operate', 'filename', 'operate_display',
            'is_success',
            'date_start',
        ]
        fields = fields_small


class UserLoginLogSerializer(serializers.ModelSerializer):
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type display'))
    status_display = serializers.ReadOnlyField(source='get_status_display', label=_('Status display'))
    mfa_display = serializers.ReadOnlyField(source='get_mfa_display', label=_('MFA display'))

    class Meta:
        model = models.UserLoginLog
        fields_mini = ['id']
        fields_small = fields_mini + [
            'username', 'type', 'type_display', 'ip', 'city', 'user_agent',
            'mfa', 'mfa_display', 'reason', 'reason_display',  'backend', 'backend_display',
            'status', 'status_display',
            'datetime',
        ]
        fields = fields_small
        extra_kwargs = {
            "user_agent": {'label': _('User agent')},
            "reason_display": {'label': _('Reason display')},
            'backend_display': {'label': _('Authentication backend')}
        }


class OperateLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', label=_('Action'))

    class Meta:
        model = models.OperateLog
        fields_mini = ['id']
        fields_small = fields_mini + [
            'user', 'action', 'action_display',
            'resource_type', 'resource_type_display', 'resource',
            'remote_addr', 'datetime', 'org_id'
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


class CommandExecutionSerializer(serializers.ModelSerializer):
    is_success = serializers.BooleanField(read_only=True, label=_('Is success'))
    hosts_display = serializers.ListSerializer(
        child=serializers.CharField(), source='hosts', read_only=True, label=_('Hosts display')
    )

    class Meta:
        model = CommandExecution
        fields_mini = ['id']
        fields_small = fields_mini + [
            'run_as', 'command', 'is_finished', 'user',
            'date_start', 'result', 'is_success', 'org_id'
        ]
        fields = fields_small + ['hosts', 'hosts_display', 'run_as_display', 'user_display']
        extra_kwargs = {
            'result': {'label': _('Result')},  # model 上的方法，只能在这修改
            'is_success': {'label': _('Is success')},
            'hosts': {'label': _('Hosts')},  # 外键，会生成 sql。不在 model 上修改
            'run_as': {'label': _('Run as')},
            'user': {'label': _('User')},
            'run_as_display': {'label': _('Run as display')},
            'user_display': {'label': _('User display')},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('user', 'run_as', 'hosts')
        return queryset


class CommandExecutionHostsRelationSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    asset_display = serializers.ReadOnlyField()
    commandexecution_display = serializers.ReadOnlyField()

    class Meta:
        model = CommandExecution.hosts.through
        fields = [
            'id', 'asset', 'asset_display', 'commandexecution', 'commandexecution_display'
        ]
