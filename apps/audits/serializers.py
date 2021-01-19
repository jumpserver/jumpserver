# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from django.db.models import F

from common.mixins import BulkSerializerMixin
from common.drf.serializers import AdaptedBulkListSerializer
from terminal.models import Session
from ops.models import CommandExecution
from . import models


class FTPLogSerializer(serializers.ModelSerializer):
    operate_display = serializers.ReadOnlyField(source='get_operate_display', label=_('Operate for display'))

    class Meta:
        model = models.FTPLog
        fields = (
            'id', 'user', 'remote_addr', 'asset', 'system_user', 'org_id',
            'operate', 'filename', 'is_success', 'date_start', 'operate_display'
        )


class UserLoginLogSerializer(serializers.ModelSerializer):
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type for display'))
    status_display = serializers.ReadOnlyField(source='get_status_display', label=_('Status for display'))
    mfa_display = serializers.ReadOnlyField(source='get_mfa_display', label=_('MFA for display'))

    class Meta:
        model = models.UserLoginLog
        fields = (
            'id', 'username', 'type', 'type_display', 'ip', 'city', 'user_agent',
            'mfa', 'reason', 'status', 'status_display', 'datetime', 'mfa_display',
            'backend'
        )
        extra_kwargs = {
            "user_agent": {'label': _('User agent')}
        }


class OperateLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OperateLog
        fields = (
            'id', 'user', 'action', 'resource_type', 'resource',
            'remote_addr', 'datetime', 'org_id'
        )


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

    class Meta:
        model = CommandExecution
        fields_mini = ['id']
        fields_small = fields_mini + [
            'run_as', 'command', 'user', 'is_finished',
            'date_start', 'result', 'is_success', 'org_id'
        ]
        fields = fields_small + ['hosts', 'run_as_display', 'user_display']
        extra_kwargs = {
            'result': {'label': _('Result')},  # model 上的方法，只能在这修改
            'is_success': {'label': _('Is success')},
            'hosts': {'label': _('Hosts')},  # 外键，会生成 sql。不在 model 上修改
            'run_as': {'label': _('Run as')},
            'user': {'label': _('User')},
            'run_as_display': {'label': _('Run as for display')},
            'user_display': {'label': _('User for display')},
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
        list_serializer_class = AdaptedBulkListSerializer
        model = CommandExecution.hosts.through
        fields = [
            'id', 'asset', 'asset_display', 'commandexecution', 'commandexecution_display'
        ]
