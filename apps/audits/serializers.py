# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from terminal.models import Session
from . import models


class FTPLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.FTPLog
        fields = '__all__'


class LoginLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserLoginLog
        fields = '__all__'


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

