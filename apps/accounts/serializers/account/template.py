from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import SecretStrategy, SecretType
from accounts.models import AccountTemplate, Account
from accounts.utils import SecretGenerator
from common.serializers import SecretReadableMixin
from common.serializers.fields import ObjectRelatedField
from .base import BaseAccountSerializer


class PasswordRulesSerializer(serializers.Serializer):
    length = serializers.IntegerField(min_value=8, max_value=30, default=16, label=_('Password length'))
    lowercase = serializers.BooleanField(default=True, label=_('Lowercase'))
    uppercase = serializers.BooleanField(default=True, label=_('Uppercase'))
    digit = serializers.BooleanField(default=True, label=_('Digit'))
    symbol = serializers.BooleanField(default=True, label=_('Special symbol'))


class AccountTemplateSerializer(BaseAccountSerializer):
    is_sync_account = serializers.BooleanField(default=False, write_only=True)
    _is_sync_account = False

    password_rules = PasswordRulesSerializer(required=False, label=_('Password rules'))
    su_from = ObjectRelatedField(
        required=False, queryset=AccountTemplate.objects, allow_null=True,
        allow_empty=True, label=_('Su from'), attrs=('id', 'name', 'username')
    )

    class Meta(BaseAccountSerializer.Meta):
        model = AccountTemplate
        fields = BaseAccountSerializer.Meta.fields + [
            'secret_strategy', 'password_rules',
            'auto_push', 'push_params', 'platforms',
            'is_sync_account', 'su_from'
        ]
        extra_kwargs = {
            'secret_strategy': {'help_text': _('Secret generation strategy for account creation')},
            'auto_push': {'help_text': _('Whether to automatically push the account to the asset')},
            'platforms': {
                'help_text': _(
                    'Associated platform, you can configure push parameters. '
                    'If not associated, default parameters will be used'
                ),
                'required': False
            },
        }

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

    @staticmethod
    def generate_secret(attrs):
        secret_type = attrs.get('secret_type', SecretType.PASSWORD)
        secret_strategy = attrs.get('secret_strategy', SecretStrategy.custom)
        password_rules = attrs.get('password_rules')
        if secret_strategy != SecretStrategy.random:
            return
        generator = SecretGenerator(secret_strategy, secret_type, password_rules)
        attrs['secret'] = generator.get_secret()

    def validate(self, attrs):
        self._is_sync_account = attrs.pop('is_sync_account', None)
        attrs = super().validate(attrs)
        self.generate_secret(attrs)
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
