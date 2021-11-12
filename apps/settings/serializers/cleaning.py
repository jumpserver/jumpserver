from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = ['CleaningSerializer']


class CleaningSerializer(serializers.Serializer):
    LOGIN_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("Login log keep days"), help_text=_("Unit: day")
    )
    TASK_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("Task log keep days"), help_text=_("Unit: day")
    )
    OPERATE_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("Operate log keep days"), help_text=_("Unit: day")
    )
    FTP_LOG_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("FTP log keep days"), help_text=_("Unit: day")
    )
    CLOUD_SYNC_TASK_EXECUTION_KEEP_DAYS = serializers.IntegerField(
        min_value=1, max_value=9999,
        label=_("Cloud sync record keep days"), help_text=_("Unit: day")
    )
    TERMINAL_SESSION_KEEP_DURATION = serializers.IntegerField(
        min_value=1, max_value=99999, required=True, label=_('Session keep duration'),
        help_text=_('Unit: days, Session, record, command will be delete if more than duration, only in database')
    )

