from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from ..application_category import DBSerializer
from applications.const import OracleVersion

__all__ = ['OracleSerializer']


class OracleSerializer(DBSerializer):
    version = serializers.ChoiceField(
        choices=OracleVersion.choices, default=OracleVersion.version_other,
        allow_null=True, label=_('Version')
    )
    port = serializers.IntegerField(default=1521, label=_('Port'), allow_null=True)
