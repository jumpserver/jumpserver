
from assets.models import Account
from common.drf.serializers import SecretReadableMixin
from .common import BaseAccountSerializer
from .account import AccountSerializer, AccountSecretSerializer


class AccountHistorySerializer(AccountSerializer):

    class Meta:
        model = Account.history.model
        fields = BaseAccountSerializer.Meta.fields_mini + \
            BaseAccountSerializer.Meta.fields_write_only + \
            BaseAccountSerializer.Meta.fields_fk + \
            ['history_id', 'date_created', 'date_updated']
        read_only_fields = fields
        ref_name = 'AccountHistorySerializer'

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields = list(set(fields) - {'org_name'})
        return fields

    def to_representation(self, instance):
        return super(AccountSerializer, self).to_representation(instance)


class AccountHistorySecretSerializer(SecretReadableMixin, AccountHistorySerializer):
    class Meta(AccountHistorySerializer.Meta):
        extra_kwargs = AccountSecretSerializer.Meta.extra_kwargs
