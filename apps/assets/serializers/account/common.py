# -*- coding: utf-8 -*-
#
from rest_framework import serializers

__all__ = ['AccountFieldsSerializerMixin']


class AccountFieldsSerializerMixin(serializers.ModelSerializer):
    class Meta:
        fields_mini = [
            'id', 'name', 'username', 'privileged',
            'platform', 'version', 'secret_type',
        ]
        fields_write_only = ['secret', 'passphrase']
        fields_other = ['date_created', 'date_updated', 'comment']
        fields_small = fields_mini + fields_write_only + fields_other
        fields_fk = ['asset']
        fields = fields_small + fields_fk
        extra_kwargs = {
            'secret': {'write_only': True},
            'passphrase': {'write_only': True},
            'token': {'write_only': True},
            'password': {'write_only': True},
        }

    def validate_name(self, value):
        if not value:
            return self.initial_data.get('username')
        return ''
