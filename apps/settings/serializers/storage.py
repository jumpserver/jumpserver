from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField

__all__ = ['StorageSettingSerializer']


class StorageSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Storage')

    FTP_FILE_MAX_STORE = serializers.IntegerField(
        required=False, allow_null=True,
        label=_('File max store'),
        help_text=_('File max store size (MB), <= 0 means no backup')
    )
    STORAGE_USAGE_THRESHOLD = serializers.IntegerField(
        required=False, allow_null=True,
        label=_('Storage usage threshold'),
        help_text=_('Storage usage threshold (percentage 0-100), 0 means no limit')
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
        help_text=_('NAS storage type: NFS or CIFS')
    )
    NAS_HOST = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=128,
        label=_('NAS host'),
        help_text=_('NAS server address, e.g. 192.168.1.100')
    )
    NAS_SHARE_NAME = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=256,
        label=_('NAS share name'),
        help_text=_('NAS share or export name')
    )
    NAS_MOUNT_PATH = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=256,
        label=_('NAS mount path'),
        help_text=_('Local mount path for NAS storage')
    )
    NAS_USERNAME = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=256,
        label=_('NAS username'),
        help_text=_('NAS login username (CIFS required)')
    )
    NAS_PASSWORD = EncryptedField(
        required=False, allow_null=True, allow_blank=True, max_length=1024,
        label=_('NAS password'),
        help_text=_('NAS login password (CIFS required)')
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
            'nas_share_name': validated_data.get('NAS_SHARE_NAME',
                                                 getattr(settings, 'NAS_SHARE_NAME', '')),
            'nas_mount_path': validated_data.get('NAS_MOUNT_PATH',
                                                 getattr(settings, 'NAS_MOUNT_PATH', '')),
            'nas_username': validated_data.get('NAS_USERNAME',
                                               getattr(settings, 'NAS_USERNAME', '')),
            'nas_password': validated_data.get('NAS_PASSWORD',
                                               getattr(settings, 'NAS_PASSWORD', '')),
        }

    def post_save(self):
        """Ensure NAS is mounted after saving settings (force re-mount)."""
        from settings.tools.nas_mount import ensure_nas_mounted, is_nas_mounted, _unmount
        config = self._get_nas_config()

        # If mount path changed, unmount the old one first
        old_mount_path = getattr(settings, 'NAS_MOUNT_PATH', '')
        new_mount_path = config.get('nas_mount_path', '')
        if old_mount_path and old_mount_path != new_mount_path:
            if is_nas_mounted(old_mount_path):
                _unmount(old_mount_path)

        ensure_nas_mounted(config, force=True)
