# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import (
    AutomationTypes, SecretType, SecretStrategy,
    SSHKeyStrategy, ChangeSecretRecordStatusChoice
)
from accounts.models import (
    Account, ChangeSecretAutomation,
    ChangeSecretRecord, AutomationExecution
)
from accounts.serializers import AuthValidateMixin, PasswordRulesSerializer
from assets.models import Asset
from common.serializers.fields import LabeledChoiceField, ObjectRelatedField
from common.utils import get_logger
from .base import BaseAutomationSerializer

logger = get_logger(__file__)

__all__ = [
    'ChangeSecretAutomationSerializer',
    'ChangeSecretRecordSerializer',
    'ChangeSecretRecordViewSecretSerializer',
    'ChangeSecretRecordBackUpSerializer',
    'ChangeSecretUpdateAssetSerializer',
    'ChangeSecretUpdateNodeSerializer',
]


def get_secret_types():
    return [
        (SecretType.PASSWORD, _('Password')),
        (SecretType.SSH_KEY, _('SSH key')),
    ]


class ChangeSecretAutomationSerializer(AuthValidateMixin, BaseAutomationSerializer):
    secret_strategy = LabeledChoiceField(
        choices=SecretStrategy.choices, required=True, label=_('Secret strategy')
    )
    ssh_key_change_strategy = LabeledChoiceField(
        choices=SSHKeyStrategy.choices, required=False, label=_('SSH Key strategy')
    )
    password_rules = PasswordRulesSerializer(required=False, label=_('Password rules'))
    secret_type = LabeledChoiceField(choices=get_secret_types(), required=True, label=_('Secret type'))

    class Meta:
        model = ChangeSecretAutomation
        read_only_fields = BaseAutomationSerializer.Meta.read_only_fields
        fields = BaseAutomationSerializer.Meta.fields + read_only_fields + [
            'secret_type', 'secret_strategy', 'secret', 'password_rules',
            'ssh_key_change_strategy', 'passphrase', 'recipients', 'params'
        ]
        extra_kwargs = {**BaseAutomationSerializer.Meta.extra_kwargs, **{
            'accounts': {'required': True, 'help_text': _('Please enter your account username')},
            'recipients': {'label': _('Recipient'), 'help_text': _(
                "Currently only mail sending is supported"
            )},
            'params': {'help_text': _(
                "Secret parameter settings, currently only effective for assets of the host type."
            )},
        }}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_ssh_key_change_strategy_choices()

    def set_ssh_key_change_strategy_choices(self):
        ssh_key_change_strategy = self.fields.get("ssh_key_change_strategy")
        if not ssh_key_change_strategy:
            return
        ssh_key_change_strategy._choices.pop(SSHKeyStrategy.add, None)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        ssh_strategy_value = data.get('ssh_key_change_strategy', {}).get('value')
        if ssh_strategy_value == SSHKeyStrategy.add:
            data['ssh_key_change_strategy'] = {
                'label': SSHKeyStrategy.set_jms.label,
                'value': SSHKeyStrategy.set_jms.value
            }
        return data

    @property
    def model_type(self):
        return AutomationTypes.change_secret

    def validate_password_rules(self, password_rules):
        secret_type = self.initial_data['secret_type']
        if secret_type != SecretType.PASSWORD:
            return password_rules

        if self.initial_data.get('secret_strategy') == SecretStrategy.custom:
            return password_rules

        return password_rules

    def validate(self, attrs):
        secret_type = attrs.get('secret_type')
        secret_strategy = attrs.get('secret_strategy')
        if secret_type == SecretType.PASSWORD:
            attrs.pop('ssh_key_change_strategy', None)
            if secret_strategy == SecretStrategy.custom:
                attrs.pop('password_rules', None)
            else:
                attrs.pop('secret', None)
        elif secret_type == SecretType.SSH_KEY:
            attrs.pop('password_rules', None)
            if secret_strategy != SecretStrategy.custom:
                attrs.pop('secret', None)
        return attrs


class ChangeSecretRecordSerializer(serializers.ModelSerializer):
    is_success = serializers.SerializerMethodField(label=_('Is success'))
    asset = ObjectRelatedField(queryset=Asset.objects, label=_('Asset'))
    account = ObjectRelatedField(
        queryset=Account.objects, label=_('Account'),
        attrs=("id", "name", "username")
    )
    execution = ObjectRelatedField(
        queryset=AutomationExecution.objects, label=_('Automation task execution')
    )

    class Meta:
        model = ChangeSecretRecord
        fields = [
            'id', 'asset', 'account', 'date_finished',
            'status', 'is_success', 'error', 'execution',
        ]
        read_only_fields = fields

    @staticmethod
    def get_is_success(obj):
        return obj.status == ChangeSecretRecordStatusChoice.success.value


class ChangeSecretRecordViewSecretSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeSecretRecord
        fields = [
            'id', 'old_secret', 'new_secret',
        ]
        read_only_fields = fields


class ChangeSecretRecordBackUpSerializer(serializers.ModelSerializer):
    asset = serializers.SerializerMethodField(label=_('Asset'))
    account = serializers.SerializerMethodField(label=_('Account'))
    is_success = serializers.SerializerMethodField(label=_('Is success'))

    class Meta:
        model = ChangeSecretRecord
        fields = [
            'id', 'asset', 'account', 'old_secret', 'new_secret',
            'status', 'error', 'is_success'
        ]
        read_only_fields = fields

    @staticmethod
    def get_asset(instance):
        return str(instance.asset)

    @staticmethod
    def get_account(instance):
        return str(instance.account)

    @staticmethod
    def get_is_success(obj):
        if obj.status == ChangeSecretRecordStatusChoice.success.value:
            return _("Success")
        return _("Failed")


class ChangeSecretUpdateAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeSecretAutomation
        fields = ['id', 'assets']


class ChangeSecretUpdateNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeSecretAutomation
        fields = ['id', 'nodes']
