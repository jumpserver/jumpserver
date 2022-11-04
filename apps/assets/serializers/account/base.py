# -*- coding: utf-8 -*-
from io import StringIO

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.utils import validate_ssh_private_key, ssh_private_key_gen
from common.drf.fields import EncryptedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from assets.models import BaseAccount

__all__ = ['BaseAccountSerializer']


class BaseAccountSerializer(BulkOrgResourceModelSerializer):
    secret = EncryptedField(
        label=_('Secret'), required=False, allow_blank=True,
        allow_null=True, max_length=40960
    )

    class Meta:
        model = BaseAccount
        fields_mini = ['id', 'name', 'username']
        fields_small = fields_mini + ['privileged', 'secret_type', 'secret', 'has_secret', 'specific']
        fields_other = ['created_by', 'date_created', 'date_updated', 'comment']
        fields = fields_small + fields_other
        read_only_fields = [
            'has_secret', 'specific',
            'date_verified', 'created_by', 'date_created',
        ]
        extra_kwargs = {
            'secret': {'write_only': True},
            'passphrase': {'write_only': True},
            'specific': {'label': _('Specific')},
        }

    def validate_private_key(self, private_key):
        if not private_key:
            return ''
        passphrase = self.initial_data.get('passphrase')
        passphrase = passphrase if passphrase else None
        valid = validate_ssh_private_key(private_key, password=passphrase)
        if not valid:
            raise serializers.ValidationError(_("private key invalid or passphrase error"))

        private_key = ssh_private_key_gen(private_key, password=passphrase)
        string_io = StringIO()
        private_key.write_private_key(string_io)
        private_key = string_io.getvalue()
        return private_key

    def validate_secret(self, value):
        secret_type = self.initial_data.get('secret_type')
        if secret_type == 'ssh_key':
            value = self.validate_private_key(value)
        return value

