from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = ['CleaningSerializer']


class CleaningSerializer(serializers.Serializer):
    LOGIN_LOG_KEEP_DAYS = serializers.IntegerField(
        default=200, required=False, label=_("Login log keep days"), help_text=_("Units: day")
    )
    TASK_LOG_KEEP_DAYS = serializers.IntegerField(
        default=90, required=False, label=_("Task log keep days"), help_text=_("Units: day")
    )
    OPERATE_LOG_KEEP_DAYS = serializers.IntegerField(
        default=200, required=False, label=_("Operate log keep days"), help_text=_("Units: day")
    )
    FTP_LOG_KEEP_DAYS = serializers.IntegerField(
        default=200, required=False, label=_("FTP log keep days"), help_text=_("Units: day")
    )
    CLOUD_SYNC_TASK_EXECUTION_KEEP_DAYS = serializers.IntegerField(
        default=200, required=False, label=_("Cloud sync record keep days"), help_text=_("Units: day")
    )
