from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from assets.models import AuthBook
from common.drf.serializers import SecretReadableMixin
from .account import AccountSerializer, AccountSecretSerializer


class AccountHistorySerializer(AccountSerializer):
    systemuser_display = serializers.SerializerMethodField(label=_('System user display'))

    class Meta:
        model = AuthBook.history.model
        fields = AccountSerializer.Meta.fields + ['history_id']
        read_only_fields = fields
        ref_name = 'AccountHistorySerializer'

    @staticmethod
    def get_systemuser_display(instance):
        if not instance.systemuser:
            return ''
        return str(instance.systemuser)

    def to_representation(self, instance):
        return super(AccountSerializer, self).to_representation(instance)


class AccountHistorySecretSerializer(SecretReadableMixin, AccountHistorySerializer):
    class Meta(AccountHistorySerializer.Meta):
        fields_backup = AccountSecretSerializer.Meta.fields_backup
        extra_kwargs = AccountSecretSerializer.Meta.extra_kwargs
