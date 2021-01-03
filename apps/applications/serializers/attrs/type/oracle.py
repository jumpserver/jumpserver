from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from ..category import DBSerializer


__all__ = ['OracleSerializer']


class OracleSerializer(DBSerializer):
    port = serializers.IntegerField(default=1521, label=_('Port'))

