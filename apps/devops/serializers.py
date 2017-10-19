# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework import serializers

from .models import *
from assets.serializers import SystemUserSerializer


class AnsibleRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnsibleRole
        fields = '__all__'


class TaskSerializer(serializers.ModelSerializer):
    ansible_role_name = serializers.SerializerMethodField()
    tags = serializers.ListField(required=False, child=serializers.CharField())

    # system_user = SystemUserSerializer()

    class Meta:
        model = Task
        exclude = ('assets', 'groups',)

    @staticmethod
    def get_ansible_role_name(obj):
        return obj.ansible_role.name
