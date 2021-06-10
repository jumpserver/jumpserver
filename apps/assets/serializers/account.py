from assets.models import AuthBook
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .base import AuthSerializerMixin


class AccountSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    class Meta:
        model = AuthBook
        fields_mini = ['id', 'username']
        fields_write_only = ['password', 'private_key', "public_key"]
        fields_small = fields_mini + fields_write_only + ['comment']
        fields_fk = ['asset', 'system_user']
        fields = fields_small + fields_fk
        extra_kwargs = {
            'username': {'required': True},
            'password': {'write_only': True},
            'private_key': {'write_only': True},
            'public_key': {'write_only': True},
        }
