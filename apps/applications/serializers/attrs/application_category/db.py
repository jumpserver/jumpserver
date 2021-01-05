# coding: utf-8
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _


__all__ = ['DBSerializer']


class DBSerializer(serializers.Serializer):
    host = serializers.CharField(max_length=128, label=_('Host'))
    port = serializers.IntegerField(label=_('Port'))
    # 添加allow_null=True，兼容之前数据库中database字段为None的情况
    database = serializers.CharField(
        max_length=128, required=True, allow_null=True, label=_('Database')
    )
