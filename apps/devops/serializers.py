# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework import serializers

from .models import *


class TaskSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    ansible_role = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = '__all__'

    @staticmethod
    def get_user(obj):
        if obj.admin_user:
            return obj.admin_user.username
        if obj.system_user:
            return obj.system_user.username

    @staticmethod
    def get_ansible_role(obj):
        return obj.ansible_role.name


class AnsibleRoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = AnsibleRole
        fields = '__all__'
