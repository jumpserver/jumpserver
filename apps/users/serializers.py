# -*- coding: utf-8 -*-
#

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


class UserActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active']


class UserGroupSerializer(serializers.ModelSerializer):
    users = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='users:user-detail-api')

    class Meta:
        model = UserGroup
        fields = '__all__'
