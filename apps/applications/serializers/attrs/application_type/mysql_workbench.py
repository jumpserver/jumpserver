from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from ..application_category import RemoteAppSerializer


__all__ = ['MySQLWorkbenchSerializer']


class MySQLWorkbenchSerializer(RemoteAppSerializer):
    MYSQL_WORKBENCH_PATH = 'C:\Program Files\MySQL\MySQL Workbench 8.0 CE\MySQLWorkbench.exe'

    path = serializers.CharField(
        max_length=128, label=_('Application path'), default=MYSQL_WORKBENCH_PATH,
        allow_null=True,
    )
    mysql_workbench_ip = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('IP'),
        allow_null=True,
    )
    mysql_workbench_port = serializers.IntegerField(
        required=False, label=_('Port'),
        allow_null=True,
    )
    mysql_workbench_name = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Database'),
        allow_null=True,
    )
    mysql_workbench_username = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Username'),
        allow_null=True,
    )
    mysql_workbench_password = serializers.CharField(
        max_length=128, allow_blank=True, required=False, write_only=True, label=_('Password'),
        allow_null=True,
    )
