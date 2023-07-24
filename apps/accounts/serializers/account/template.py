from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import AccountTemplate, Account
from common.serializers import SecretReadableMixin
from common.serializers.fields import ObjectRelatedField
from .base import BaseAccountSerializer


class AccountTemplateSerializer(BaseAccountSerializer):
    is_sync_account = serializers.BooleanField(default=False, write_only=True)
    _is_sync_account = False

    su_from = ObjectRelatedField(
        required=False, queryset=AccountTemplate.objects, allow_null=True,
        allow_empty=True, label=_('Su from'), attrs=('id', 'name', 'username')
    )

    class Meta(BaseAccountSerializer.Meta):
        model = AccountTemplate
        fields = BaseAccountSerializer.Meta.fields + ['is_sync_account', 'su_from']

    def sync_accounts_secret(self, instance, diff):
        if not self._is_sync_account or 'secret' not in diff:
            return
        query_data = {
            'source_id': instance.id,
            'username': instance.username,
            'secret_type': instance.secret_type
        }
        accounts = Account.objects.filter(**query_data)
        instance.bulk_sync_account_secret(accounts, self.context['request'].user.id)

    def validate(self, attrs):
        self._is_sync_account = attrs.pop('is_sync_account', None)
        attrs = super().validate(attrs)
        return attrs

    def update(self, instance, validated_data):
        diff = {
            k: v for k, v in validated_data.items()
            if getattr(instance, k, None) != v
        }
        instance = super().update(instance, validated_data)
        if {'username', 'secret_type'} & set(diff.keys()):
            Account.objects.filter(source_id=instance.id).update(source_id=None)
        else:
            self.sync_accounts_secret(instance, diff)
        return instance


class AccountTemplateSecretSerializer(SecretReadableMixin, AccountTemplateSerializer):
    class Meta(AccountTemplateSerializer.Meta):
        extra_kwargs = {
            'secret': {'write_only': False},
        }
