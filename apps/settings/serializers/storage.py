from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.settings.serializers.cleaning import MIN_VALUE
from common.serializers.fields import EncryptedField
from ..const import NAS_MOUNT_PATH

__all__ = ['StorageSettingSerializer']


class StorageSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Storage')

    FTP_FILE_MAX_STORE = serializers.IntegerField(
        required=True,min_value=0,
        label=_('File max store'),
        help_text=_('File max store size (MB), <= 0 means no backup')
    )
    STORAGE_USAGE_THRESHOLD = serializers.IntegerField(
        required=True,min_value=0, max_value=100,
        label=_('Storage usage threshold'),
        help_text=_('Storage usage threshold (percentage 0-100), 0 means no limit')
    )
    STORAGE_RECLAMATION_METHOD = serializers.ChoiceField(
        required=False, default='delete_day',
        choices=(
            ('delete_day', _('Delete the earliest day of audit')),
            ('archive_day', _('Archive the earliest day of audit')),
            ('delete_month', _('Delete the earliest month of audit')),
            ('archive_month', _('Archive the earliest month of audit')),
        ),
        label=_('Storage reclamation method'),
        help_text=_('Archive means move files to NAS storage and then delete local files')
    )
    STORAGE_RECLAMATION_TARGETS = serializers.ListField(
        required=False, default=list,
        child=serializers.ChoiceField(
            choices=[
                ('session_replay', _('Session replay')),
                ('file_transfer', _('File transfer')),
            ]
        ),
        label=_('Storage reclamation targets'),
        help_text=_('Select which data to clean during storage reclamation')
    )

    # NAS storage
    NAS_ENABLED = serializers.BooleanField(
        required=False, default=False,
        label=_('NAS enabled'),
        help_text=_('Enable NAS storage')
    )
    NAS_TYPE = serializers.ChoiceField(
        choices=(('nfs', 'NFS'), ('cifs', 'CIFS')),
        required=False, allow_null=True, allow_blank=True,
        label=_('NAS type'),
        help_text=_('NAS storage type: windows or linux')
    )
    NAS_HOST = serializers.CharField(
        required=True, allow_null=True, allow_blank=True, max_length=128,
        label=_('NAS host'),
        help_text=_('NAS server address, e.g. 192.168.1.100')
    )
    NAS_PORT = serializers.IntegerField(
        required=True, allow_null=True, min_value=0, max_value=65535,
        label=_('NAS port'),
        help_text=_('NAS port, 0 means use the default port')
    )
    NAS_SHARE_NAME = serializers.CharField(
        required=True, allow_null=True, allow_blank=True, max_length=256,
        label=_('NAS share name'),
        help_text=_('NAS share or export name')
    )
    NAS_USERNAME = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=256,
        label=_('NAS username'),
        help_text=_('NAS login username (windows required)')
    )
    NAS_PASSWORD = EncryptedField(
        required=False, allow_null=True, allow_blank=True, max_length=1024,
        label=_('NAS password'),
        help_text=_('NAS login password (windows required)')
    )

    def _get_nas_config(self):
        """Get NAS config from validated data, fall back to settings."""
        validated_data = getattr(self, 'validated_data', {})
        return {
            'nas_enabled': validated_data.get('NAS_ENABLED',
                                              getattr(settings, 'NAS_ENABLED', False)),
            'nas_type': validated_data.get('NAS_TYPE',
                                           getattr(settings, 'NAS_TYPE', 'nfs')),
            'nas_host': validated_data.get('NAS_HOST',
                                           getattr(settings, 'NAS_HOST', '')),
            'nas_port': validated_data.get('NAS_PORT',
                                           getattr(settings, 'NAS_PORT', 0)),
            'nas_share_name': validated_data.get('NAS_SHARE_NAME',
                                                 getattr(settings, 'NAS_SHARE_NAME', '')),
            'nas_mount_path': NAS_MOUNT_PATH,
            'nas_username': validated_data.get('NAS_USERNAME',
                                               getattr(settings, 'NAS_USERNAME', '')),
            'nas_password': validated_data.get('NAS_PASSWORD',
                                               getattr(settings, 'NAS_PASSWORD', '')),
        }

    def post_save(self):
        """Ensure NAS is mounted after saving settings (force re-mount)."""
        from settings.tools.nas_mount import ensure_nas_mounted
        config = self._get_nas_config()
        ensure_nas_mounted(config, force=True)
