# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from .models import Role, User, UserGroup


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields =