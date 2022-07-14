from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from assets.models import AuthBook
from common.drf.serializers import SecretReadableMixin
from .account import AccountSerializer, AccountSecretSerializer


class AccountHistorySerializer(AccountSerializer):
    systemuser_display = serializers.SerializerMethodField(label=_('System user display'))

    class Meta:
        model = AuthBook.history.model
        fields = AccountSerializer.Meta.fields_mini + \
                 AccountSerializer.Meta.fields_write_only + \
                 AccountSerializer.Meta.fields_fk + \
                 ['history_id', 'date_created', 'date_updated']
        read_only_fields = fields
        ref_name = 'AccountHistorySerializer'

    @staticmethod
    def get_systemuser_display(instance):
        if not instance.systemuser:
            return ''
        return str(instance.systemuser)

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields = list(set(fields) - {'org_name'})
        return fields

    def to_representation(self, instance):
        return super(AccountSerializer, self).to_representation(instance)


class AccountHistorySecretSerializer(SecretReadableMixin, AccountHistorySerializer):
    class Meta(AccountHistorySerializer.Meta):
        extra_kwargs = AccountSecretSerializer.Meta.extra_kwargs
