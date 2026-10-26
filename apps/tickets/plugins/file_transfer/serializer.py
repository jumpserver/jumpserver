from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..resources import AssetAccountRequestSerializer


class RequestSerializer(AssetAccountRequestSerializer):
    accounts = serializers.ListField(child=serializers.CharField(max_length=128), allow_empty=False,
                                    max_length=1, label=_('Account'),
                                    style={'resource': 'account', 'depends_on': 'asset'})
    direction = serializers.ChoiceField(choices=[('upload', _('Upload')), ('download', _('Download'))], label=_('Direction'))
    paths = serializers.ListField(child=serializers.CharField(max_length=4096), allow_empty=True,
                                 max_length=20, required=False, default=list, label=_('File paths'))
    target_directory = serializers.CharField(max_length=4096, required=False, allow_blank=True, default='',
                                            label=_('Target directory'))
    files = serializers.ListField(child=serializers.UUIDField(), max_length=20, required=False, default=list,
                                  label=_('Files'))
    duration = serializers.IntegerField(min_value=60, max_value=86400, default=3600, label=_('Validity (seconds)'))

    invalid_accounts_message = _('Select active accounts with existing access.')

    def get_accounts(self, asset_id):
        from assets.models import Asset
        from .permissions import base_access
        asset = Asset.objects.filter(pk=asset_id, org_id=self.context['org_id'], is_active=True,
                                     platform__category='host', platform__type='linux').first()
        access = base_access(self.context['request'].user, asset) if asset else {}
        ids = [pk for pk, value in access.items() if {'ssh', 'sftp'} & set(value['protocols'])]
        return super().get_accounts(asset_id).filter(pk__in=ids, is_active=True, secret_type__in=['password', 'ssh_key'])

    def validate(self, attrs):
        from django.utils import timezone
        from tickets.models import TicketTransferFile
        from .policy import validate_path
        attrs = super().validate(attrs)
        if self.get_accounts(attrs['asset']).filter(username=attrs['accounts'][0]).count() != 1:
            raise serializers.ValidationError({'accounts': _('Select an unambiguous password or SSH key account.')})
        if attrs['direction'] == 'upload':
            if not attrs['files'] or not attrs['target_directory'] or attrs['paths']:
                raise serializers.ValidationError(_('Provide files and a target directory for upload.'))
            attrs['target_directory'] = validate_path(attrs['target_directory'])
            ids = attrs['files']
            files = TicketTransferFile.objects.filter(
                pk__in=ids, owner=self.context['request'].user, org_id=self.context['org_id'],
                kind='upload', ticket__isnull=True, purged_at__isnull=True, expires_at__gt=timezone.now(),
            )
            if len(set(ids)) != len(ids) or files.count() != len(ids):
                raise serializers.ValidationError({'files': _('Upload available files belonging to this organization.')})
            if len(set(files.values_list('name', flat=True))) != len(ids):
                raise serializers.ValidationError({'files': _('Duplicate file names are not allowed.')})
        else:
            if not attrs['paths'] or attrs['files'] or attrs['target_directory']:
                raise serializers.ValidationError(_('Provide exact file paths for download.'))
            attrs['paths'] = [validate_path(path) for path in attrs['paths']]
            if len(set(attrs['paths'])) != len(attrs['paths']) or '/' in attrs['paths']:
                raise serializers.ValidationError({'paths': _('Provide distinct file paths.')})
        return attrs
