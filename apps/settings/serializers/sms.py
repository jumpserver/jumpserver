from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class SMSBackendSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=256, required=True, label=_('Name'))
    label = serializers.CharField(max_length=256, required=True, label=_('Label'))
