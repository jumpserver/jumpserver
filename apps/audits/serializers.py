# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from terminal.models import Session
from ops.models import CommandExecution
from . import models


class FTPLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.FTPLog
        fields = (
            'user', 'remote_addr', 'asset', 'system_user',
            'operate', 'filename', 'is_success', 'date_start'
        )


class UserLoginLogSerializer(serializers.ModelSerializer):
    type_display = serializers.ReadOnlyField(source='get_type_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    mfa_display = serializers.ReadOnlyField(source='get_mfa_display')

    class Meta:
        model = models.UserLoginLog
        fields = (
            'username', 'type', 'type_display', 'ip', 'city', 'user_agent',
            'mfa', 'reason', 'status', 'status_display', 'datetime', 'mfa_display'
        )


class OperateLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OperateLog
        fields = (
            'user', 'action', 'resource_type', 'resource',
            'remote_addr', 'datetime'
        )


class PasswordChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PasswordChangeLog
        fields = (
            'user', 'change_by', 'remote_addr', 'datetime'
        )


class SessionAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = '__all__'


class CommandExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommandExecution
        fields = (
            'hosts', 'run_as', 'command', 'user', 'is_finished',
            'date_start', 'result', 'is_success'
        )
