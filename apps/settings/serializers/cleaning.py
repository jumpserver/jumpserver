from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = ['CleaningSerializer']


class CleaningSerializer(serializers.Serializer):
    LOGIN_LOG_KEEP_DAYS = serializers.IntegerField(
        label=_("Login log keep days"), help_text=_("Unit: day")
    )
    TASK_LOG_KEEP_DAYS = serializers.IntegerField(
        label=_("Task log keep days"), help_text=_("Unit: day")
    )
    OPERATE_LOG_KEEP_DAYS = serializers.IntegerField(
        label=_("Operate log keep days"), help_text=_("Unit: day")
    )
    FTP_LOG_KEEP_DAYS = serializers.IntegerField(
        label=_("FTP log keep days"), help_text=_("Unit: day")
    )
    CLOUD_SYNC_TASK_EXECUTION_KEEP_DAYS = serializers.IntegerField(
        label=_("Cloud sync record keep days"), help_text=_("Unit: day")
    )
