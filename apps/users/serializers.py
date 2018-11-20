# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.validators import ValidationError
from rest_framework_bulk import BulkListSerializer

from common.utils import get_signer, validate_ssh_public_key
from common.mixins import BulkSerializerMixin
from .models import User, UserGroup

signer = get_signer()


class UserSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    groups_display = serializers.SerializerMethodField()
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=UserGroup.objects.all(), required=False)

    class Meta:
        model = User
        list_serializer_class = BulkListSerializer
        exclude = [
            'first_name', 'last_name', 'password', '_private_key',
            '_public_key', '_otp_secret_key', 'user_permissions'
        ]
        # validators = []

    def get_field_names(self, declared_fields, info):
        fields = super(UserSerializer, self).get_field_names(declared_fields, info)
        fields.extend([
            'groups_display', 'get_role_display',
            'get_source_display', 'is_valid'
        ])
        return fields

    @staticmethod
    def get_groups_display(obj):
        return " ".join([group.name for group in obj.groups.all()])


class ServiceAccountSerializer(serializers.ModelSerializer):
    access_key = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'access_key']
        read_only_fields = ['id', 'access_key']

    def get_username(self):
        return self.initial_data.get('name')

    def get_email(self):
        name = self.initial_data.get('name')
        return '{}@serviceaccount.local'.format(name)

    def validate_name(self, name):
        email = self.get_email()
        username = self.get_username()
        if User.objects.filter(email=email) or \
                User.objects.filter(username=username):
            raise ValidationError('name not unique', code='unique')
        return name

    def create(self, validated_data):
        validated_data['email'] = self.get_email()
        validated_data['username'] = self.get_username()
        validated_data['role'] = User.ROLE_APP
        instance = super().create(validated_data)
        return instance

    @staticmethod
    def get_access_key(obj):
        if obj.access_keys.count() > 0:
            return 'Hidden'
        else:
            access_key = obj.create_access_key()
            return access_key.get_full_value()


class UserPKUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', '_public_key']

    @staticmethod
    def validate__public_key(value):
        if not validate_ssh_public_key(value):
            raise serializers.ValidationError(_('Not a valid ssh public key'))
        return value


class UserUpdateGroupSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=UserGroup.objects.all())

    class Meta:
        model = User
        fields = ['id', 'groups']


class UserGroupSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    users = serializers.SerializerMethodField()

    class Meta:
        model = UserGroup
        list_serializer_class = BulkListSerializer
        fields = '__all__'
        read_only_fields = ['id', 'created_by']

    @staticmethod
    def get_users(obj):
        return [user.name for user in obj.users.all()]


class UserGroupUpdateMemeberSerializer(serializers.ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all())

    class Meta:
        model = UserGroup
        fields = ['id', 'users']


class ChangeUserPasswordSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['password']
