# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from .models import ApplyPermission

class ApplyPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplyPermission
        fields = '__all__'

