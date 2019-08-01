# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from rest_framework import serializers

from common.utils import ssh_pubkey_gen, validate_ssh_private_key


class AuthSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=1024)
    private_key = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=4096)

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


class ConnectivitySerializer(serializers.Serializer):
    status = serializers.IntegerField()
    datetime = serializers.DateTimeField()


class AuthSerializerMixin:
    def validate_password(self, password):
        return password

    def validate_private_key(self, private_key):
        if not private_key:
            return
        if 'OPENSSH' in private_key:
            msg = _("Not support openssh format key, using "
                    "ssh-keygen -t rsa -m pem to generate")
            raise serializers.ValidationError(msg)
        password = self.initial_data.get("password")
        valid = validate_ssh_private_key(private_key, password)
        if not valid:
            raise serializers.ValidationError(_("private key invalid"))
        return private_key

    def validate_public_key(self, public_key):
        return public_key

    @staticmethod
    def clean_auth_fields(validated_data):
        for field in ('password', 'private_key', 'public_key'):
            value = validated_data.get(field)
            if not value:
                validated_data.pop(field, None)

        # print(validated_data)
        # raise serializers.ValidationError(">>>>>>")

    def create(self, validated_data):
        self.clean_auth_fields(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self.clean_auth_fields(validated_data)
        return super().update(instance, validated_data)
