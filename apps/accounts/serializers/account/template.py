from rest_framework import serializers

from accounts.models import AccountTemplate, Account
from common.serializers import SecretReadableMixin
from .base import BaseAccountSerializer


class AccountTemplateSerializer(BaseAccountSerializer):
    is_sync_account = serializers.BooleanField(default=False, write_only=True)
    _is_sync_account = False

    class Meta(BaseAccountSerializer.Meta):
        model = AccountTemplate
        fields = BaseAccountSerializer.Meta.fields + ['is_sync_account']

    def sync_accounts_secret(self, instance, diff):
        if not self._is_sync_account or 'secret' not in diff:
            return

        accounts = Account.objects.filter(source_id=instance.id)
        instance.bulk_sync_account_secret(accounts, self.context['request'].user.id)

    def validate(self, attrs):
        self._is_sync_account = attrs.pop('is_sync_account', None)
        attrs = super().validate(attrs)
        return attrs

    def update(self, instance, validated_data):
        diff = {
            k: v for k, v in validated_data.items()
            if getattr(instance, k) != v
        }
        instance = super().update(instance, validated_data)
        self.sync_accounts_secret(instance, diff)
        return instance


class AccountTemplateSecretSerializer(SecretReadableMixin, AccountTemplateSerializer):
    class Meta(AccountTemplateSerializer.Meta):
        extra_kwargs = {
            'secret': {'write_only': False},
        }
