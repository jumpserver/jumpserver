# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin

from common.utils import signer, validate_ssh_public_key
from .models import User, UserGroup


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
            print('Not a valid key')
            print(value)
            raise serializers.ValidationError(_('Not a valid ssh public key'))
        return value


class UserUpdateGroupSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=UserGroup.objects.all())

    class Meta:
        model = User
        fields = ['id', 'groups']


class UserGroupSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    user_amount = serializers.SerializerMethodField()

    class Meta:
        model = UserGroup
        list_serializer_class = BulkListSerializer
        fields = '__all__'

    @staticmethod
    def get_user_amount(obj):
        return obj.users.count()


class UserGroupUpdateMemeberSerializer(serializers.ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all())

    class Meta:
        model = UserGroup
        fields = ['id', 'users']


# class GroupDetailSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = UserGroup
#         fields = ['id', 'name', 'comment', 'date_created', 'created_by', 'users']


# class UserBulkUpdateSerializer(BulkSerializerMixin, serializers.ModelSerializer):
#     group_display = serializers.SerializerMethodField()
#     active_display = serializers.SerializerMethodField()
#     groups = serializers.PrimaryKeyRelatedField(many=True, queryset=UserGroup.objects.all())
#
#     class Meta(object):
#         model = User
#         list_serializer_class = BulkListSerializer
#         fields = ['id', 'is_active', 'username', 'name', 'email', 'role', 'avatar',
#                   'enable_otp', 'comment', 'groups', 'get_role_display',
#                   'group_display', 'active_display']
#
#     @staticmethod
#     def get_group_display(obj):
#         return " ".join([group.name for group in obj.groups.all()])
#
#     @staticmethod
#     def get_active_display(obj):
#         TODO: user active state
        # return not (obj.is_expired and obj.is_active)
#
#
# class GroupBulkUpdateSerializer(BulkSerializerMixin, serializers.ModelSerializer):
#     user_amount = serializers.SerializerMethodField()
#
#     class Meta:
#         model = UserGroup
#         list_serializer_class = BulkListSerializer
#         fields = ['id', 'name', 'comment', 'user_amount']
#
#     @staticmethod
#     def get_user_amount(obj):
#         return obj.users.count()
#
