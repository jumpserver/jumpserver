# -*- coding: utf-8 -*-
#
from io import StringIO

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.utils import ssh_pubkey_gen, ssh_private_key_gen, validate_ssh_private_key
from common.drf.fields import EncryptedField
from .utils import validate_password_for_ansible


class AuthValidateMixin(serializers.Serializer):
    password = EncryptedField(
        label=_('Password'), required=False, allow_blank=True, allow_null=True,
        max_length=1024, validators=[validate_password_for_ansible]
    )
    private_key = EncryptedField(
        label=_('SSH private key'), required=False, allow_blank=True,
        allow_null=True, max_length=16384
    )
    passphrase = serializers.CharField(
        allow_blank=True, allow_null=True, required=False, max_length=512,
        write_only=True, label=_('Key password')
    )

    def validate_private_key(self, private_key):
        if not private_key:
            return
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

    @staticmethod
    def clean_auth_fields(validated_data):
        for field in ('password', 'private_key', 'public_key'):
            value = validated_data.get(field)
            if not value:
                validated_data.pop(field, None)
        validated_data.pop('passphrase', None)

    @staticmethod
    def _validate_gen_key(attrs):
        private_key = attrs.get('private_key')
        if not private_key:
            return attrs

        password = attrs.get('passphrase')
        username = attrs.get('username')
        public_key = ssh_pubkey_gen(private_key, password=password, username=username)
        attrs['public_key'] = public_key
        return attrs

    def validate(self, attrs):
        attrs = self._validate_gen_key(attrs)
        return super().validate(attrs)

    def create(self, validated_data):
        self.clean_auth_fields(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self.clean_auth_fields(validated_data)
        return super().update(instance, validated_data)
