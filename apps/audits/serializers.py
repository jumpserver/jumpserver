# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from django.db.models import F

from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer
from terminal.models import Session
from ops.models import CommandExecution
from . import models


class FTPLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.FTPLog
        fields = (
            'id', 'user', 'remote_addr', 'asset', 'system_user',
            'operate', 'filename', 'is_success', 'date_start'
        )


class UserLoginLogSerializer(serializers.ModelSerializer):
    type_display = serializers.ReadOnlyField(source='get_type_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    mfa_display = serializers.ReadOnlyField(source='get_mfa_display')

    class Meta:
        model = models.UserLoginLog
        fields = (
            'id', 'username', 'type', 'type_display', 'ip', 'city', 'user_agent',
            'mfa', 'reason', 'status', 'status_display', 'datetime', 'mfa_display'
        )


class OperateLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OperateLog
        fields = (
            'id', 'user', 'action', 'resource_type', 'resource',
            'remote_addr', 'datetime'
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
            'date_start', 'result', 'is_success'
        ]
        fields = fields_small + ['hosts', 'run_as_display', 'user_display']
        extra_kwargs = {
            'result': {'label': _('Result')},  # model 上的方法，只能在这修改
            'is_success': {'label': _('Is success')},
            'hosts': {'label': _('Hosts')},  # 外键，会生成 sql。不在 model 上修改
            'run_as': {'label': _('Run as')},
            'user': {'label': _('User')},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.annotate(user_display=F('user__name'))\
            .annotate(run_as_display=F('run_as__name'))
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
