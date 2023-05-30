from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

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
    TERMINAL_SESSION_KEEP_DURATION = serializers.IntegerField(
        min_value=1, max_value=99999, required=True, label=_('Session keep duration (day)'),
        help_text=_('Session, record, command will be delete if more than duration, only in database, OSS will not be affected.')
    )
    ACTIVITY_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("Activity log keep days (day)"),
    )
