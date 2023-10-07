from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.serializers import ValidationError

__all__ = ['CleaningSerializer']


class CleaningSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Period clean')

    LOGIN_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("Login log keep days (day)"),
    )
    TASK_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("Task log keep days (day)"),
    )
    OPERATE_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("Operate log keep days (day)"),
    )
    FTP_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("FTP log keep days (day)"),
    )
    CLOUD_SYNC_TASK_EXECUTION_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("Cloud sync record keep days (day)"),
    )
    ACTIVITY_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("Activity log keep days (day)"),
    )
    TERMINAL_SESSION_KEEP_DURATION = serializers.IntegerField(
        min_value=1, max_value=99999, required=True, label=_('Session keep duration (day)'),
        help_text=_(
            'Session, record, command will be delete if more than duration, only in database, OSS will not be affected.')
    )
    MIN_DAYS_THRESHOLD = 180

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not settings.LIMIT_SUPER_PRIV:
            return attrs

        error_names = [
            name for name in settings.LOG_NAMES
            if attrs.get(name, 0) < self.MIN_DAYS_THRESHOLD
        ]
        if error_names:
            error_message = _('must be greater than {} days.').format(self.MIN_DAYS_THRESHOLD)
            raise ValidationError({name: error_message for name in error_names})
        return attrs
