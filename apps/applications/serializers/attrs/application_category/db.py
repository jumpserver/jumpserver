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
    use_ssl = serializers.BooleanField(default=False, label=_('Use SSL'))
    ca_cert = serializers.CharField(
        required=False, allow_null=True, label=_('CA certificate')
    )
    client_cert = serializers.CharField(
        required=False, allow_null=True, label=_('Client certificate file')
    )
    cert_key = serializers.CharField(
        required=False, allow_null=True, label=_('Certificate key file')
    )
    allow_invalid_cert = serializers.BooleanField(default=False, label=_('Allow invalid cert'))
