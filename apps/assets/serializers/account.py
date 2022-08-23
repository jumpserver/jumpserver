from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.db.models import F

from assets.models import Account
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .base import AuthSerializerMixin
from common.drf.serializers import SecretReadableMixin


class AccountSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    ip = serializers.ReadOnlyField(label=_("IP"))
    asset_name = serializers.ReadOnlyField(label=_("Asset"))
    platform = serializers.ReadOnlyField(label=_("Platform"))

    class Meta:
        model = Account
        fields_mini = [
            'id', 'privileged', 'username', 'ip', 'asset_name',
            'platform', 'version'
        ]
        fields_write_only = ['password', 'private_key', 'public_key', 'passphrase']
        fields_other = ['date_created', 'date_updated', 'connectivity', 'date_verified', 'comment']
        fields_small = fields_mini + fields_write_only + fields_other
        fields_fk = ['asset']
        fields = fields_small + fields_fk
        extra_kwargs = {
            'username': {'required': True},
            'private_key': {'write_only': True},
            'public_key': {'write_only': True},
        }
        ref_name = 'AssetAccountSerializer'

    def validate(self, attrs):
        attrs = self._validate_gen_key(attrs)
        return attrs

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('asset')\
            .annotate(ip=F('asset__ip')) \
            .annotate(asset_name=F('asset__name'))
        return queryset


class AccountSecretSerializer(SecretReadableMixin, AccountSerializer):
    class Meta(AccountSerializer.Meta):
        fields_backup = [
            'name', 'ip', 'platform', 'protocols', 'username', 'password',
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
