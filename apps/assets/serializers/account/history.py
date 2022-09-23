
from assets.models import Account
from common.drf.serializers import SecretReadableMixin
from .base import BaseAccountSerializer
from .account import AccountSerializer, AccountSecretSerializer


class AccountHistorySerializer(AccountSerializer):
    class Meta:
        model = Account.history.model
        fields = BaseAccountSerializer.Meta.fields_mini
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
