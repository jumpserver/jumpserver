# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from ..models import User

__all__ = ['UserUserGroupRelationSerializer']


class UserUserGroupRelationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(read_only=True)
    usergroup_name = serializers.CharField(read_only=True)

    class Meta:
        model = User.groups.through
        fields = ['id', 'user', 'user_name', 'usergroup', 'usergroup_name']
