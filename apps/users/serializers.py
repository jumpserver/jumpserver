# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from .models import User, UserGroup


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = [
            'password', 'first_name', 'last_name', 'secret_key_otp',
            'private_key', 'public_key', 'avatar',
        ]


class UserGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGroup
        fields = '__all__'


