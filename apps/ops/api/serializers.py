# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals, print_function
from ..models import HostAlia, UserAlia, CmdAlia, RunasAlia, Extra_conf, Privilege, Sudo
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


