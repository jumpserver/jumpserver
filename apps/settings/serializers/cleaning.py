from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = ['CleaningSerializer']

MIN_VALUE = 180 if settings.LIMIT_SUPER_PRIV else 1


class CleaningSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Period clean')

    LOGIN_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Login log keep days (day)"),
    )
    TASK_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Task log keep days (day)"),
    )
    OPERATE_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Operate log keep days (day)"),
    )
    PASSWORD_CHANGE_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("password change log keep days (day)"),
    )
    FTP_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("FTP log keep days (day)"),
    )
    CLOUD_SYNC_TASK_EXECUTION_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Cloud sync record keep days (day)"),
    )
    JOB_EXECUTION_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("job execution keep days (day)"),
    )
    ACTIVITY_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=9999,
        label=_("Activity log keep days (day)"),
    )
    TERMINAL_SESSION_KEEP_DURATION = serializers.IntegerField(
        min_value=MIN_VALUE, max_value=99999, required=True, label=_('Session keep duration (day)'),
        help_text=_(
            'Session, record, command will be delete if more than duration, only in database, OSS will not be affected.')
    )
