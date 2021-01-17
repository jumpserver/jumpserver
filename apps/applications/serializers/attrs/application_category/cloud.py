from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _


__all__ = ['CloudSerializer']


class CloudSerializer(serializers.Serializer):
    cluster = serializers.CharField(max_length=1024, label=_('Cluster'), allow_null=True)
