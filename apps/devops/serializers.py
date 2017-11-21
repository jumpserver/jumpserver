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
        exclude = ('assets', 'groups', 'counts')

    @staticmethod
    def get_ansible_role_name(obj):
        return obj.ansible_role.name


class TaskUpdateGroupSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=AssetGroup.objects.all())

    class Meta:
        model = Task
        fields = ['id', 'groups']


class TaskUpdateAssetSerializer(serializers.ModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = Task
        fields = ['id', 'assets']


class TaskUpdateSystemUserSerializer(serializers.ModelSerializer):
    system_user = serializers.PrimaryKeyRelatedField(many=False, queryset=SystemUser.objects.all(), allow_null=True)

    class Meta:
        model = Task
        fields = ['id', 'system_user']


class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Record
        fields = '__all__'


class VariableSerializer(serializers.ModelSerializer):

    class Meta:
        model = Variable
        exclude = ('assets', 'groups')

