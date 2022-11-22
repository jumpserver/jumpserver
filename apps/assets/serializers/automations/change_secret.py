# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext as _
from rest_framework import serializers

from common.utils import get_logger
from common.drf.fields import LabeledChoiceField, ObjectRelatedField
from assets.serializers.base import AuthValidateMixin
from assets.const import DEFAULT_PASSWORD_RULES, SecretType, SecretStrategy, SSHKeyStrategy
from assets.models import Asset, Account, ChangeSecretAutomation, ChangeSecretRecord, AutomationExecution

from .base import BaseAutomationSerializer

logger = get_logger(__file__)

__all__ = [
    'ChangeSecretAutomationSerializer',
    'ChangeSecretRecordSerializer',
    'ChangeSecretRecordBackUpSerializer'
]


class ChangeSecretAutomationSerializer(AuthValidateMixin, BaseAutomationSerializer):
    secret_strategy = LabeledChoiceField(
        choices=SecretStrategy.choices, required=True, label=_('Secret strategy')
    )
    ssh_key_change_strategy = LabeledChoiceField(
        choices=SSHKeyStrategy.choices, required=False, label=_('SSH Key strategy')
    )
    password_rules = serializers.DictField(default=DEFAULT_PASSWORD_RULES)

    class Meta:
        model = ChangeSecretAutomation
        read_only_fields = BaseAutomationSerializer.Meta.read_only_fields
        fields = BaseAutomationSerializer.Meta.fields + read_only_fields + [
            'secret_type', 'secret_strategy', 'secret', 'password_rules',
            'ssh_key_change_strategy', 'passphrase', 'recipients',
        ]
        extra_kwargs = {**BaseAutomationSerializer.Meta.extra_kwargs, **{
            'recipients': {'label': _('Recipient'), 'help_text': _(
                "Currently only mail sending is supported"
            )},
        }}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_secret_type_choices()

    def set_secret_type_choices(self):
        secret_type = self.fields.get('secret_type')
        if not secret_type:
            return
        choices = secret_type._choices
        choices.pop(SecretType.ACCESS_KEY, None)
        choices.pop(SecretType.TOKEN, None)
        secret_type._choices = choices

    def validate_password_rules(self, password_rules):
        secret_type = self.initial_secret_type
        if secret_type != SecretType.PASSWORD:
            return password_rules

        length = password_rules.get('length')
        symbol_set = password_rules.get('symbol_set', '')

        try:
            length = int(length)
        except Exception as e:
            logger.error(e)
            msg = _("* Please enter the correct password length")
            raise serializers.ValidationError(msg)
        if length < 6 or length > 30:
            msg = _('* Password length range 6-30 bits')
            raise serializers.ValidationError(msg)

        if not isinstance(symbol_set, str):
            symbol_set = str(symbol_set)

        password_rules = {'length': length, 'symbol_set': ''.join(symbol_set)}
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
    account = ObjectRelatedField(queryset=Account.objects, label=_('Account'))
    execution = ObjectRelatedField(
        queryset=AutomationExecution.objects, label=_('Automation task execution')
    )

    class Meta:
        model = ChangeSecretRecord
        fields = [
            'id', 'asset', 'account', 'date_started', 'date_finished',
            'timedelta', 'is_success', 'error', 'execution',
        ]
        read_only_fields = fields

    @staticmethod
    def get_is_success(obj):
        if obj.status == 'success':
            return _("Success")
        return _("Failed")


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
        if obj.status == 'success':
            return _("Success")
        return _("Failed")
