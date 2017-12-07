# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import serializers

from .models import AdHoc


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdHoc
        fields = '__all__'


