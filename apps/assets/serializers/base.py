# -*- coding: utf-8 -*-
#

from collections import OrderedDict
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

    def validate_public_key(self, public_key):
        return public_key

    def validate_private_key(self, private_key):
        if not private_key:
            return
        if 'OPENSSH' in private_key:
            msg = _("Not support openssh format key, "
                    "using ssh-keygen -t rsa -m pem to generate")
            raise serializers.ValidationError(msg)
        return private_key

    @staticmethod
    def union_validate_private_key(private_key, attrs):
        if not private_key:
            return
        password = attrs.get("password")
        valid = validate_ssh_private_key(private_key, password)
        if not valid:
            raise serializers.ValidationError(_("private key invalid"))
        return private_key

    @staticmethod
    def clean_auth_fields(validated_data):
        for field in ('password', 'private_key', 'public_key'):
            value = validated_data.get(field)
            if not value:
                validated_data.pop(field, None)

    def create(self, validated_data):
        self.clean_auth_fields(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self.clean_auth_fields(validated_data)
        return super().update(instance, validated_data)


class UnionValidateSerializerMixin:

    def to_final_value(self, attrs):
        fields = self._writable_fields
        for field in fields:
            if field.field_name not in attrs.keys():
                continue
            get_final_method = getattr(self, 'get_final_' + field.field_name, None)
            if get_final_method is None:
                continue
            value = attrs.get(field.field_name)
            final_value = get_final_method(value, attrs)
            attrs[field.field_name] = final_value
        return attrs

    def validate(self, attrs):
        attrs = super().validate(attrs)

        # 获取字段最终的值（会根据其他字段联合确定）
        attrs = self.to_final_value(attrs)

        errors = OrderedDict()
        fields = self._writable_fields

        for field in fields:
            if field.field_name not in attrs.keys():
                continue
            union_validate_method = getattr(self, 'union_validate_' + field.field_name, None)
            if union_validate_method is None:
                continue
            try:
                value = attrs.get(field.field_name)
                union_validate_value = union_validate_method(value, attrs)
            except serializers.ValidationError as exc:
                errors[field.field_name] = exc.detail
            else:
                attrs[field.field_name] = union_validate_value

        if errors:
            raise serializers.ValidationError(errors)

        return attrs
