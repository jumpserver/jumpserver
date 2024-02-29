# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from audits.backends.db import OperateLogStore
from common.serializers.fields import LabeledChoiceField, ObjectRelatedField
from common.utils import reverse, i18n_trans
from common.utils.timezone import as_current_tz
from ops.serializers.job import JobExecutionSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from terminal.models import Session
from users.models import User
from . import models
from .const import (
    ActionChoices, OperateChoices,
    MFAChoices, LoginStatusChoices,
    LoginTypeChoices, ActivityChoices,
)


class JobLogSerializer(JobExecutionSerializer):
    class Meta:
        model = models.JobLog
        read_only_fields = [
            "id", "material", 'job_type', "time_cost", 'date_start',
            'date_finished', 'date_created',
            'is_finished', 'is_success',
            'task_id', 'creator_name'
        ]
        fields = read_only_fields + []
        extra_kwargs = {
            "creator_name": {"label": _("Creator")},
        }


class FTPLogSerializer(serializers.ModelSerializer):
    operate = LabeledChoiceField(choices=OperateChoices.choices, label=_("Operate"))

    class Meta:
        model = models.FTPLog
        fields_mini = ["id"]
        fields_small = fields_mini + [
            "user", "remote_addr", "asset", "account",
            "org_id", "operate", "filename", "date_start",
            "is_success", "has_file",
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
        fields = ('diff',)

    def to_representation(self, instance):
        return {'diff': OperateLogStore.convert_diff_friendly(instance)}


class OperateLogSerializer(BulkOrgResourceModelSerializer):
    action = LabeledChoiceField(choices=ActionChoices.choices, label=_("Action"))
    resource = serializers.SerializerMethodField(label=_("Resource"))
    resource_type = serializers.SerializerMethodField(label=_('Resource Type'))

    class Meta:
        model = models.OperateLog
        fields_mini = ["id"]
        fields_small = fields_mini + [
            "user", "action", "resource_type",
            "resource", "remote_addr", "datetime",
            "org_id",
        ]
        fields = fields_small

    @staticmethod
    def get_resource_type(instance):
        return _(instance.resource_type)

    @staticmethod
    def get_resource(instance):
        return i18n_trans(instance.resource)


class PasswordChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PasswordChangeLog
        fields = ("id", "user", "change_by", "remote_addr", "datetime")


class SessionAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = "__all__"


class ActivityUnionLogSerializer(serializers.Serializer):
    id = serializers.CharField()
    timestamp = serializers.SerializerMethodField()
    detail_url = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    r_type = serializers.CharField(read_only=True)

    @staticmethod
    def get_timestamp(obj):
        return as_current_tz(obj['datetime']).strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def get_content(obj):
        if not obj['r_detail']:
            action = obj['r_action'].replace('_', ' ').capitalize()
            ctn = _('User %s %s this resource') % (obj['r_user'], _(action))
        else:
            ctn = i18n_trans(obj['r_detail'])
        return ctn

    @staticmethod
    def get_detail_url(obj):
        detail_url = ''
        detail_id, obj_type = obj['r_detail_id'], obj['r_type']
        if not detail_id:
            return detail_url

        if obj_type == ActivityChoices.operate_log:
            detail_url = '%s?%s' % (
                reverse(
                    'audits:operate-log-detail',
                    kwargs={'pk': obj['id']},
                ), 'type=action_detail')
        elif obj_type == ActivityChoices.task:
            detail_url = reverse(
                'ops:celery-task-log', kwargs={'pk': detail_id}
            )
        elif obj_type == ActivityChoices.login_log:
            detail_url = reverse(
                'audits:login-log-detail',
                kwargs={'pk': detail_id},
                api_to_ui=True, is_audit=True
            )
        return detail_url


class FileSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=True)


class UserSessionSerializer(serializers.ModelSerializer):
    type = LabeledChoiceField(choices=LoginTypeChoices.choices, label=_("Type"))
    user = ObjectRelatedField(required=False, queryset=User.objects, label=_('User'))
    date_expired = serializers.DateTimeField(format="%Y/%m/%d %H:%M:%S", label=_('Date expired'))
    is_current_user_session = serializers.SerializerMethodField()

    class Meta:
        model = models.UserSession
        fields_mini = ['id']
        fields_small = fields_mini + [
            'type', 'ip', 'city', 'user_agent', 'user', 'is_current_user_session',
            'backend', 'backend_display', 'is_active', 'date_created', 'date_expired'
        ]
        fields = fields_small
        extra_kwargs = {
            "backend_display": {"label": _("Authentication backend")},
        }

    def get_is_current_user_session(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        return request.session.session_key == obj.key
