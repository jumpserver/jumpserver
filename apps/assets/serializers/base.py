# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from common.utils import ssh_pubkey_gen


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
