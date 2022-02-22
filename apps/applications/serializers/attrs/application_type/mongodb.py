from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from ..application_category import DBSerializer

__all__ = ['MongoDBSerializer']


class MongoDBSerializer(DBSerializer):
    port = serializers.IntegerField(default=27017, label=_('Port'), allow_null=True)

