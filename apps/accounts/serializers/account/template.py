from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import AccountTemplate
from common.serializers import SecretReadableMixin
from common.serializers.fields import ObjectRelatedField
from .base import BaseAccountSerializer


class PasswordRulesSerializer(serializers.Serializer):
    length = serializers.IntegerField(min_value=8, max_value=30, default=16, label=_('Password length'))
    lowercase = serializers.BooleanField(default=True, label=_('Lowercase'))
    uppercase = serializers.BooleanField(default=True, label=_('Uppercase'))
    digit = serializers.BooleanField(default=True, label=_('Digit'))
    symbol = serializers.BooleanField(default=True, label=_('Special symbol'))
    exclude_symbols = serializers.CharField(
        default='', allow_blank=True, max_length=16, label=_('Exclude symbol')
    )


class AccountTemplateSerializer(BaseAccountSerializer):
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
            'su_from'
        ]
        extra_kwargs = {
            **BaseAccountSerializer.Meta.extra_kwargs,
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


class AccountTemplateSecretSerializer(SecretReadableMixin, AccountTemplateSerializer):
    class Meta(AccountTemplateSerializer.Meta):
        fields = AccountTemplateSerializer.Meta.fields + ['spec_info']
        extra_kwargs = {
            **AccountTemplateSerializer.Meta.extra_kwargs,
            'secret': {'write_only': False},
            'spec_info': {'label': _('Spec info')},
        }
