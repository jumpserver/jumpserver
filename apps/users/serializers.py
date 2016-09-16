# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

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
        fields = ['id', '_private_key']

    def validate__private_key(self, value):
        from users.utils import validate_ssh_pk
        checked, reason = validate_ssh_pk(value)
        if not checked:
            raise serializers.ValidationError(_('Not a valid ssh private key.'))
        return value
