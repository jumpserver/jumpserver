import copy

from applications import const
from . import application_category, application_type

__all__ = [
    'category_serializer_classes_mapping',
    'type_serializer_classes_mapping',
    'get_serializer_class_by_application_type',
    'type_secret_serializer_classes_mapping'
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
    const.AppType.redis.value: application_type.RedisSerializer,
    const.AppType.mariadb.value: application_type.MariaDBSerializer,
    const.AppType.oracle.value: application_type.OracleSerializer,
    const.AppType.pgsql.value: application_type.PostgreSerializer,
    const.AppType.sqlserver.value: application_type.SQLServerSerializer,
    # cloud
    const.AppType.k8s.value: application_type.K8SSerializer
}

remote_app_serializer_classes_mapping = {
    # remote-app
    const.AppType.chrome.value: application_type.ChromeSerializer,
    const.AppType.mysql_workbench.value: application_type.MySQLWorkbenchSerializer,
    const.AppType.vmware_client.value: application_type.VMwareClientSerializer,
    const.AppType.custom.value: application_type.CustomSerializer
}

type_serializer_classes_mapping.update(remote_app_serializer_classes_mapping)

remote_app_secret_serializer_classes_mapping = {
    # remote-app
    const.AppType.chrome.value: application_type.ChromeSecretSerializer,
    const.AppType.mysql_workbench.value: application_type.MySQLWorkbenchSecretSerializer,
    const.AppType.vmware_client.value: application_type.VMwareClientSecretSerializer,
    const.AppType.custom.value: application_type.CustomSecretSerializer
}

type_secret_serializer_classes_mapping = copy.deepcopy(type_serializer_classes_mapping)

type_secret_serializer_classes_mapping.update(remote_app_secret_serializer_classes_mapping)


def get_serializer_class_by_application_type(_application_type):
    return type_serializer_classes_mapping.get(_application_type)
