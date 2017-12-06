# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import serializers

from .models import Playbook


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Playbook
        fields = '__all__'


