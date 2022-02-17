from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from ..application_category import DBSerializer

__all__ = ['RedisSerializer']


class RedisSerializer(DBSerializer):
    port = serializers.IntegerField(default=6379, label=_('Port'), allow_null=True)

