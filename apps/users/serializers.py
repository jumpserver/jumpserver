# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin

from .models import User, UserGroup


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='users:user-group-detail-api')

    class Meta:
        model = User
        exclude = [
            'password', 'first_name', 'last_name', 'secret_key_otp',
            'private_key', 'public_key', 'avatar',
        ]


class UserGroupSerializer(serializers.ModelSerializer):
    users = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='users:user-detail-api')

    class Meta:
        model = UserGroup
        fields = '__all__'


class GroupEditSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserGroup
        fields = ['id', 'name', 'comment', 'date_created', 'created_by']


class UserAttributeSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['avatar', 'wechat', 'phone', 'enable_otp', 'comment', 'is_active', 'name']


class UserGroupEditSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=UserGroup.objects.all())

    class Meta:
        model = User
        fields = ['id', 'groups']


class UserPKUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', '_public_key']

    def validate__public_key(self, value):
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

    def get_group_display(self, obj):
        return " ".join([group.name for group in obj.groups.all()])

    def get_active_display(self, obj):
        # TODO: user ative state
        return not (obj.is_expired and obj.is_active)
