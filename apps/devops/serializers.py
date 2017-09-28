# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = '__all__'

    @staticmethod
    def get_user(obj):
        if obj.admin_user:
            return obj.admin_user.username
        if obj.system_user:
            return obj.system_user.username
