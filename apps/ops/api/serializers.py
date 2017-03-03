# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from ops.models import *
from rest_framework import serializers


class HostAliaSerializer(serializers.ModelSerializer):

    class Meta:
        model = HostAlia


class CmdAliaSerializer(serializers.ModelSerializer):

    class Meta:
        model = CmdAlia


class UserAliaSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserAlia


class RunasAliaSerializer(serializers.ModelSerializer):

    class Meta:
        model = RunasAlia


class ExtraconfSerializer(serializers.ModelSerializer):

    class Meta:
        model = Extra_conf


class PrivilegeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Privilege


class SudoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Sudo


class CronTableSerializer(serializers.ModelSerializer):

    class Meta:
        model = CronTable

class TaskSerializer(serializers.ModelSerializer):
    sub_tasks = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Task
        read_only_fields = ('record',)

class SubTaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubTask
