from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from assets.models import AuthBook
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .base import AuthSerializerMixin


class AccountSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    ip = serializers.ReadOnlyField(label=_("IP"))
    hostname = serializers.ReadOnlyField(label=_("Hostname"))

    class Meta:
        model = AuthBook
        fields_mini = ['id', 'username', 'ip', 'hostname', 'version']
        fields_write_only = ['password', 'private_key', "public_key"]
        fields_other = ['date_created', 'date_updated', 'connectivity', 'date_verified', 'comment']
        fields_small = fields_mini + fields_write_only + fields_other
        fields_fk = ['asset', 'systemuser', 'systemuser_display']
        fields = fields_small + fields_fk
        extra_kwargs = {
            'username': {'required': True},
            'password': {'write_only': True},
            'private_key': {'write_only': True},
            'public_key': {'write_only': True},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('systemuser', 'asset')
        return queryset


class AccountSecretSerializer(AccountSerializer):
    class Meta(AccountSerializer.Meta):
        extra_kwargs = {
            'password': {'write_only': False},
            'private_key': {'write_only': False},
            'public_key': {'write_only': False},
        }


class AccountTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('test', 'test'),
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    task = serializers.CharField(read_only=True)
