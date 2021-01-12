# coding: utf-8
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _


__all__ = ['DBSerializer']


class DBSerializer(serializers.Serializer):
    host = serializers.CharField(max_length=128, label=_('Host'), allow_null=True)
    port = serializers.IntegerField(label=_('Port'), allow_null=True)
    database = serializers.CharField(
        max_length=128, required=True, allow_null=True, label=_('Database')
    )
