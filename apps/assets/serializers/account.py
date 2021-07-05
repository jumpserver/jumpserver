from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from assets.models import AuthBook
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .base import AuthSerializerMixin


class AccountSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    ip = serializers.ReadOnlyField(label=_("IP"))
    hostname = serializers.ReadOnlyField(label=_("Hostname"))
    username_display = serializers.ReadOnlyField(label=_("Username"))

    class Meta:
        model = AuthBook
        fields_mini = ['id', 'username', 'username_display', 'ip', 'hostname', 'version']
        fields_write_only = ['password', 'private_key', "public_key"]
        fields_other = ['date_created', 'date_updated', 'comment']
        fields_small = fields_mini + fields_write_only + fields_other
        fields_fk = ['asset', 'systemuser']
        fields = fields_small + fields_fk
        extra_kwargs = {
            'username': {'required': True},
            'password': {'write_only': True},
            'private_key': {'write_only': True},
            'public_key': {'write_only': True},
        }


class AccountSecretSerializer(AccountSerializer):
    class Meta(AccountSerializer.Meta):
        extra_kwargs = {
            'username': {'required': True},
            'password': {'write_only': False},
            'private_key': {'write_only': False},
            'public_key': {'write_only': False},
        }
