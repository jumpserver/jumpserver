from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = ['StorageSettingSerializer']


class StorageSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Storage')

    FTP_FILE_MAX_STORE = serializers.IntegerField(
        required=False, allow_null=True,
        label=_('FTP file max store'),
        help_text=_('FTP file upload max store size (MB), <= 0 means no backup')
    )
    STORAGE_USAGE_THRESHOLD = serializers.IntegerField(
        required=False, allow_null=True,
        label=_('Storage usage threshold'),
        help_text=_('Storage usage threshold (MB), 0 means no limit')
    )
