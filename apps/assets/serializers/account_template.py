from assets.models import AccountTemplate
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .base import AuthSerializerMixin
from .account import AccountSerializer


class AccountTemplateSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    class Meta:
        model = AccountTemplate
        fields_mini = ['id', 'privileged', 'username', 'name']
        fields_write_only = AccountSerializer.Meta.fields_write_only
        fields_other = AccountSerializer.Meta.fields_other
        fields = fields_mini + fields_write_only + fields_other
        extra_kwargs = AccountSerializer.Meta.extra_kwargs

    def validate(self, attrs):
        print(attrs)

        raise ValueError('test')
        attrs = self._validate_gen_key(attrs)
        return attrs
