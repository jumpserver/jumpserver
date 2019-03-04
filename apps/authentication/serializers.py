# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from .models import AccessKey


__all__ = ['AccessKeySerializer']


class AccessKeySerializer(serializers.ModelSerializer):

    class Meta:
        model = AccessKey
        fields = ['id', 'secret']
        read_only_fields = ['id', 'secret']
