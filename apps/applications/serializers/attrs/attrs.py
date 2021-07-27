from rest_framework import serializers
from applications import const
from . import application_category, application_type


__all__ = [
    'category_serializer_classes_mapping',
    'type_serializer_classes_mapping',
    'get_serializer_class_by_application_type',
]


# define `attrs` field `category serializers mapping`
# ---------------------------------------------------

category_serializer_classes_mapping = {
    const.AppCategory.db.value: application_category.DBSerializer,
    const.AppCategory.remote_app.value: application_category.RemoteAppSerializer,
    const.AppCategory.cloud.value: application_category.CloudSerializer,
}

# define `attrs` field `type serializers mapping`
# -----------------------------------------------

type_serializer_classes_mapping = {
    # db
    const.AppType.mysql.value: application_type.MySQLSerializer,
    const.AppType.mariadb.value: application_type.MariaDBSerializer,
    const.AppType.oracle.value: application_type.OracleSerializer,
    const.AppType.pgsql.value: application_type.PostgreSerializer,
    # remote-app
    const.AppType.chrome.value: application_type.ChromeSerializer,
    const.AppType.mysql_workbench.value: application_type.MySQLWorkbenchSerializer,
    const.AppType.vmware_client.value: application_type.VMwareClientSerializer,
    const.AppType.custom.value: application_type.CustomSerializer,
    # cloud
    const.AppType.k8s.value: application_type.K8SSerializer
}


def get_serializer_class_by_application_type(_application_type):
    return type_serializer_classes_mapping.get(_application_type)
