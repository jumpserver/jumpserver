# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.drf.fields import LabeledChoiceField
from ops.models.job import JobAuditLog
from ops.serializers.job import JobExecutionSerializer
from terminal.models import Session
from . import models
from .const import (
    ActionChoices,
    OperateChoices,
    MFAChoices,
    LoginStatusChoices,
    LoginTypeChoices,
)


class JobAuditLogSerializer(JobExecutionSerializer):
    class Meta:
        model = JobAuditLog
        read_only_fields = ["timedelta", "time_cost", 'is_finished', 'date_start',
                            'date_finished',
                            'date_created',
                            'is_success',
                            'creator_name']
        fields = read_only_fields + []


class FTPLogSerializer(serializers.ModelSerializer):
    operate = LabeledChoiceField(choices=OperateChoices.choices, label=_("Operate"))

    class Meta:
        model = models.FTPLog
        fields_mini = ["id"]
        fields_small = fields_mini + [
            "user",
            "remote_addr",
            "asset",
            "system_user",
            "org_id",
            "operate",
            "filename",
            "is_success",
            "date_start",
        ]
        fields = fields_small


class UserLoginLogSerializer(serializers.ModelSerializer):
    mfa = LabeledChoiceField(choices=MFAChoices.choices, label=_("MFA"))
    type = LabeledChoiceField(choices=LoginTypeChoices.choices, label=_("Type"))
    status = LabeledChoiceField(choices=LoginStatusChoices.choices, label=_("Status"))

    class Meta:
        model = models.UserLoginLog
        fields_mini = ["id"]
        fields_small = fields_mini + [
            "username", "type", "ip",
            "city", "user_agent", "mfa",
            "reason", "reason_display",
            "backend", "backend_display",
            "status", "datetime",
        ]
        fields = fields_small
        extra_kwargs = {
            "user_agent": {"label": _("User agent")},
            "reason_display": {"label": _("Reason display")},
            "backend_display": {"label": _("Authentication backend")},
        }


class OperateLogActionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OperateLog
        fields = ('before', 'after')


class OperateLogSerializer(serializers.ModelSerializer):
    action = LabeledChoiceField(choices=ActionChoices.choices, label=_("Action"))

    class Meta:
        model = models.OperateLog
        fields_mini = ["id"]
        fields_small = fields_mini + [
            "user", "action", "resource_type",
            "resource_type_display", "resource",
            "remote_addr", "datetime", "org_id",
        ]
        fields = fields_small
        extra_kwargs = {"resource_type_display": {"label": _("Resource Type")}}


class PasswordChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PasswordChangeLog
        fields = ("id", "user", "change_by", "remote_addr", "datetime")


class SessionAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = "__all__"
