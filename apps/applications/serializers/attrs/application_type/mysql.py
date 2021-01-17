from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from ..application_category import DBSerializer


__all__ = ['MySQLSerializer']


class MySQLSerializer(DBSerializer):
    port = serializers.IntegerField(default=3306, label=_('Port'), allow_null=True)




