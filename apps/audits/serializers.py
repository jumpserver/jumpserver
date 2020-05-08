# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from terminal.models import Session
from . import models


class FTPLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.FTPLog
        fields = '__all__'


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
        fields = '__all__'


class PasswordChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PasswordChangeLog
        fields = '__all__'


class SessionAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = '__all__'

