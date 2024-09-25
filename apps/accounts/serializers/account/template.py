from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import SecretStrategy, SecretType
from accounts.models import AccountTemplate
from accounts.utils import SecretGenerator
from common.serializers import SecretReadableMixin
from common.serializers.fields import ObjectRelatedField
from .base import BaseAccountSerializer


class PasswordRulesSerializer(serializers.Serializer):
    length = serializers.IntegerField(min_value=8, max_value=36, default=16, label=_('Password length'))
    lowercase = serializers.BooleanField(default=True, label=_('Lowercase'))
    uppercase = serializers.BooleanField(default=True, label=_('Uppercase'))
    digit = serializers.BooleanField(default=True, label=_('Digit'))
    symbol = serializers.BooleanField(default=True, label=_('Special symbol'))
    exclude_symbols = serializers.CharField(
        default='', allow_blank=True, max_length=16, label=_('Exclude symbol')
    )

    @staticmethod
    def get_render_help_text():
        return _("""length is the length of the password, and the range is 8 to 30.
lowercase indicates whether the password contains lowercase letters, 
uppercase indicates whether it contains uppercase letters,
digit indicates whether it contains numbers, and symbol indicates whether it contains special symbols.
exclude_symbols is used to exclude specific symbols. You can fill in the symbol characters to be excluded (up to 16). 
If you do not need to exclude symbols, you can leave it blank.
default: {"length": 16, "lowercase": true, "uppercase": true, "digit": true, "symbol": true, "exclude_symbols": ""}""")


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
        fields_unimport_template = ['push_params']

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
        attrs = super().validate(attrs)
        self.generate_secret(attrs)
        return attrs


class AccountTemplateSecretSerializer(SecretReadableMixin, AccountTemplateSerializer):
    class Meta(AccountTemplateSerializer.Meta):
        fields = AccountTemplateSerializer.Meta.fields + ['spec_info']
        extra_kwargs = {
            **AccountTemplateSerializer.Meta.extra_kwargs,
            'secret': {'write_only': False},
            'spec_info': {'label': _('Spec info')},
        }
