from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from assets.models import AuthBook
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .base import AuthSerializerMixin
from common.utils.encode import ssh_pubkey_gen
from common.drf.serializers import SecretReadableMixin


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
            'private_key': {'write_only': True},
            'public_key': {'write_only': True},
            'systemuser_display': {'label': _('System user display')}
        }
        ref_name = 'AssetAccountSerializer'

    def _validate_gen_key(self, attrs):
        private_key = attrs.get('private_key')
        if not private_key:
            return attrs

        password = attrs.get('passphrase')
        username = attrs.get('username')
        public_key = ssh_pubkey_gen(private_key, password=password, username=username)
        attrs['public_key'] = public_key
        return attrs

    def validate(self, attrs):
        attrs = self._validate_gen_key(attrs)
        return attrs

    def get_protocols(self, v):
        """ protocols 是 queryset 中返回的，Post 创建成功后返回序列化时没有这个字段 """
        if hasattr(v, 'protocols'):
            protocols = v.protocols
        elif hasattr(v, 'asset') and v.asset:
            protocols = v.asset.protocols
        else:
            protocols = ''
        protocols = protocols.replace(' ', ', ')
        return protocols

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('systemuser', 'asset')
        return queryset

    def to_representation(self, instance):
        instance.load_auth()
        return super().to_representation(instance)


class AccountSecretSerializer(SecretReadableMixin, AccountSerializer):
    class Meta(AccountSerializer.Meta):
        extra_kwargs = {
            'password': {'write_only': False},
            'private_key': {'write_only': False},
            'public_key': {'write_only': False},
            'systemuser_display': {'label': _('System user display')}
        }


class AccountBackUpSerializer(AccountSecretSerializer):
    class Meta(AccountSecretSerializer.Meta):
        fields = [
            'id', 'hostname', 'ip', 'username', 'password',
            'private_key', 'public_key', 'date_created',
            'date_updated', 'version'
        ]

    @classmethod
    def setup_eager_loading(cls, queryset):
        return queryset

    def to_representation(self, instance):
        return super(AccountSerializer, self).to_representation(instance)


class AccountTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('test', 'test'),
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    task = serializers.CharField(read_only=True)
