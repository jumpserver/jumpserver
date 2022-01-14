from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from assets.models import AuthBook
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .base import AuthSerializerMixin
from .utils import validate_password_contains_left_double_curly_bracket


class AccountSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    ip = serializers.ReadOnlyField(label=_("IP"))
    hostname = serializers.ReadOnlyField(label=_("Hostname"))
    platform = serializers.ReadOnlyField(label=_("Platform"))
    protocols = serializers.SerializerMethodField(label=_("Protocols"))
    date_created = serializers.DateTimeField(
        label=_('Date created'), format="%Y/%m/%d %H:%M:%S", read_only=True
    )
    date_updated = serializers.DateTimeField(
        label=_('Date updated'), format="%Y/%m/%d %H:%M:%S", read_only=True
    )

    class Meta:
        model = AuthBook
        fields_mini = ['id', 'username', 'ip', 'hostname', 'platform', 'protocols', 'version']
        fields_write_only = ['password', 'private_key', "public_key", 'passphrase']
        fields_other = ['date_created', 'date_updated', 'connectivity', 'date_verified', 'comment']
        fields_small = fields_mini + fields_write_only + fields_other
        fields_fk = ['asset', 'systemuser', 'systemuser_display']
        fields = fields_small + fields_fk
        extra_kwargs = {
            'username': {'required': True},
            'password': {
                'write_only': True,
                "validators": [validate_password_contains_left_double_curly_bracket]
            },
            'private_key': {'write_only': True},
            'public_key': {'write_only': True},
            'systemuser_display': {'label': _('System user display')}
        }
        ref_name = 'AssetAccountSerializer'

    def get_protocols(self, v):
        return v.protocols.replace(' ', ', ')

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('systemuser', 'asset')
        return queryset

    def to_representation(self, instance):
        instance.load_auth()
        return super().to_representation(instance)


class AccountSecretSerializer(AccountSerializer):
    class Meta(AccountSerializer.Meta):
        fields_backup = [
            'hostname', 'ip', 'platform', 'protocols', 'username', 'password',
            'private_key', 'public_key', 'date_created', 'date_updated', 'version'
        ]
        extra_kwargs = {
            'password': {'write_only': False},
            'private_key': {'write_only': False},
            'public_key': {'write_only': False},
            'systemuser_display': {'label': _('System user display')}
        }


class AccountTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('test', 'test'),
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    task = serializers.CharField(read_only=True)
