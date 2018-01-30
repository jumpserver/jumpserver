# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework_bulk import BulkListSerializer

from common.utils import get_signer, validate_ssh_public_key
from common.mixins import BulkSerializerMixin
from .models import User, UserGroup

signer = get_signer()


class UserSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    groups_display = serializers.SerializerMethodField()
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=UserGroup.objects.all())

    class Meta:
        model = User
        list_serializer_class = BulkListSerializer
        exclude = ['first_name', 'last_name', 'password', '_private_key', '_public_key']

    def get_field_names(self, declared_fields, info):
        fields = super(UserSerializer, self).get_field_names(declared_fields, info)
        fields.extend(['groups_display', 'get_role_display', 'is_valid'])
        return fields

    @staticmethod
    def get_groups_display(obj):
        return " ".join([group.name for group in obj.groups.all()])


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
