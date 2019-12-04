# coding: utf-8
# 

from rest_framework import serializers

__all__ = ['PublicSettingSerializer']


class PublicSettingSerializer(serializers.Serializer):
    data = serializers.DictField(read_only=True)
