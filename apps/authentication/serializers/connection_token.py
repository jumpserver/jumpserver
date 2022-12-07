from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from ..models import ConnectionToken

__all__ = [
    'ConnectionTokenSerializer', 'SuperConnectionTokenSerializer',
]


class ConnectionTokenSerializer(OrgResourceModelSerializerMixin):
    expire_time = serializers.IntegerField(read_only=True, label=_('Expired time'))

    class Meta:
        model = ConnectionToken
        fields_mini = ['id', 'value']
        fields_small = fields_mini + [
            'user', 'asset', 'account', 'input_username',
            'input_secret', 'connect_method', 'protocol', 'actions',
            'date_expired', 'date_created', 'date_updated', 'created_by',
            'updated_by', 'org_id', 'org_name',
        ]
        read_only_fields = [
            # 普通 Token 不支持指定 user
            'user', 'expire_time',
            'user_display', 'asset_display',
        ]
        fields = fields_small + read_only_fields
        extra_kwargs = {
            'value': {'read_only': True},
        }

    def get_user(self, attrs):
        request = self.context.get('request')
        user = request.user if request else None
        return user


class SuperConnectionTokenSerializer(ConnectionTokenSerializer):
    class Meta(ConnectionTokenSerializer.Meta):
        read_only_fields = list(set(ConnectionTokenSerializer.Meta.read_only_fields) - {'user'})

    def get_user(self, attrs):
        return attrs.get('user')
