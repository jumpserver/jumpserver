# -*- coding: utf-8 -*-
#
from io import StringIO

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.utils import ssh_pubkey_gen, ssh_private_key_gen, validate_ssh_private_key
from common.drf.fields import EncryptedField
from assets.models import Type
from .utils import validate_password_for_ansible


class AuthSerializer(serializers.ModelSerializer):
    password = EncryptedField(required=False, allow_blank=True, allow_null=True, max_length=1024, label=_('Password'))
    private_key = EncryptedField(required=False, allow_blank=True, allow_null=True, max_length=16384, label=_('Private key'))

    def gen_keys(self, private_key=None, password=None):
        if private_key is None:
            return None, None
        public_key = ssh_pubkey_gen(private_key=private_key, password=password)
        return private_key, public_key

    def save(self, **kwargs):
        password = self.validated_data.pop('password', None) or None
        private_key = self.validated_data.pop('private_key', None) or None
        self.instance = super().save(**kwargs)
        if password or private_key:
            private_key, public_key = self.gen_keys(private_key, password)
            self.instance.set_auth(password=password, private_key=private_key,
                                   public_key=public_key)
        return self.instance


class AuthSerializerMixin(serializers.ModelSerializer):
    password = EncryptedField(
        label=_('Password'), required=False, allow_blank=True, allow_null=True, max_length=1024,
        validators=[validate_password_for_ansible]
    )
    private_key = EncryptedField(
        label=_('SSH private key'), required=False, allow_blank=True, allow_null=True, max_length=16384
    )
    passphrase = serializers.CharField(
        allow_blank=True, allow_null=True, required=False, max_length=512,
        write_only=True, label=_('Key password')
    )

    def validate_password(self, password):
        return password

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

    def validate_public_key(self, public_key):
        return public_key

    @staticmethod
    def clean_auth_fields(validated_data):
        for field in ('password', 'private_key', 'public_key'):
            value = validated_data.get(field)
            if not value:
                validated_data.pop(field, None)
        validated_data.pop('passphrase', None)

    def create(self, validated_data):
        self.clean_auth_fields(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self.clean_auth_fields(validated_data)
        return super().update(instance, validated_data)


class TypesField(serializers.MultipleChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = Type.CHOICES
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        return Type.value_to_choices(value)

    def to_internal_value(self, data):
        if data is None:
            return data
        return Type.choices_to_value(data)


class ActionsDisplayField(TypesField):
    def to_representation(self, value):
        values = super().to_representation(value)
        choices = dict(Type.CHOICES)
        return [choices.get(i) for i in values]
