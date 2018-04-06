# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from .models import FTPLog


class FTPLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = FTPLog
        fields = '__all__'
