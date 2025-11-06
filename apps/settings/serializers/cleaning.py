from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = ['CleaningSerializer']

MIN_VALUE = 180 if settings.LIMIT_SUPER_PRIV else 1


class CleaningSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Period clean')

    LOGIN_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Login log retention days"),
    )
    TASK_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Task log retention days"),
    )
    OPERATE_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Operate log retention days"),
    )
    PASSWORD_CHANGE_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Password change log retention days"),
    )
    FTP_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("FTP log retention days"),
    )
    CLOUD_SYNC_TASK_EXECUTION_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Cloud sync task history retention days"),
    )
    JOB_EXECUTION_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("job execution retention days"),
    )
    ACTIVITY_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Activity log retention days"),
    )
    TERMINAL_SESSION_KEEP_DURATION = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=99999, required=True, label=_('Session log retention days'),
        help_text=_(
            'Session, record, command will be delete if more than duration, only in database, OSS will not be affected.')
    )

    ACCOUNT_CHANGE_SECRET_RECORD_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Change secret and push record retention days"),
    )
