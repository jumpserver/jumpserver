# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from .models import Role, User, UserGroup


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ['first_name', 'last_name', 'is_staff']


class UserGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGroup
        fields = '__all__'


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'
