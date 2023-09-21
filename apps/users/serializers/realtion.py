# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from ..models import User

__all__ = ['User2GroupRelationSerializer']


class User2GroupRelationSerializer(serializers.ModelSerializer):
    user_display = serializers.CharField(read_only=True)
    usergroup_display = serializers.CharField(read_only=True)

    class Meta:
        model = User.groups.through
        fields = [
            'id', 'user', 'user_display',
            'usergroup', 'usergroup_display'
        ]
