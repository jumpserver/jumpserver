# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin

from common.utils import unsign
from .models import User, UserGroup


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['avatar', 'wechat', 'phone', 'enable_otp', 'comment', 'is_active', 'name']


class UserPKUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', '_public_key']

    @staticmethod
    def validate__public_key(value):
        from sshpubkeys import SSHKey
        from sshpubkeys.exceptions import InvalidKeyException
        ssh = SSHKey(value)
        try:
            ssh.parse()
        except InvalidKeyException as e:
            print e
            raise serializers.ValidationError(_('Not a valid ssh public key'))
        except NotImplementedError as e:
            print e
            raise serializers.ValidationError(_('Not a valid ssh public key'))
        return value


class UserAndGroupSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=UserGroup.objects.all())

    class Meta:
        model = User
        fields = ['id', 'groups']


class GroupDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGroup
        fields = ['id', 'name', 'comment', 'date_created', 'created_by', 'users']


class UserBulkUpdateSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    group_display = serializers.SerializerMethodField()
    active_display = serializers.SerializerMethodField()
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=UserGroup.objects.all())

    class Meta(object):
        model = User
        list_serializer_class = BulkListSerializer
        fields = ['id', 'is_active', 'username', 'name', 'email', 'role', 'avatar',
                  'enable_otp', 'comment', 'groups', 'get_role_display',
                  'group_display', 'active_display']

    @staticmethod
    def get_group_display(obj):
        return " ".join([group.name for group in obj.groups.all()])

    @staticmethod
    def get_active_display(obj):
        # TODO: user active state
        return not (obj.is_expired and obj.is_active)


class GroupBulkUpdateSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    user_amount = serializers.SerializerMethodField()

    class Meta:
        model = UserGroup
        list_serializer_class = BulkListSerializer
        fields = ['id', 'name', 'comment', 'user_amount']

    @staticmethod
    def get_user_amount(obj):
        return obj.users.count()


class AppUserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=20)

    def create(self, validated_data):
        sign = validated_data('username', '')
        username = unsign(sign)
        pass

    def update(self, instance, validated_data):
        pass
