from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from ..application_category import DBSerializer

__all__ = ['SQLServerSerializer']


class SQLServerSerializer(DBSerializer):
    port = serializers.IntegerField(default=1433, label=_('Port'), allow_null=True)

