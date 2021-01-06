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
    const.ApplicationCategoryChoices.db.value: application_category.DBSerializer,
    const.ApplicationCategoryChoices.remote_app.value: application_category.RemoteAppSerializer,
    const.ApplicationCategoryChoices.cloud.value: application_category.CloudSerializer,
}

# define `attrs` field `type serializers mapping`
# -----------------------------------------------

type_serializer_classes_mapping = {
    # db
    const.ApplicationTypeChoices.mysql.value: application_type.MySQLSerializer,
    const.ApplicationTypeChoices.mariadb.value: application_type.MariaDBSerializer,
    const.ApplicationTypeChoices.oracle.value: application_type.OracleSerializer,
    const.ApplicationTypeChoices.pgsql.value: application_type.PostgreSerializer,
    # remote-app
    const.ApplicationTypeChoices.chrome.value: application_type.ChromeSerializer,
    const.ApplicationTypeChoices.mysql_workbench.value: application_type.MySQLWorkbenchSerializer,
    const.ApplicationTypeChoices.vmware_client.value: application_type.VMwareClientSerializer,
    const.ApplicationTypeChoices.custom.value: application_type.CustomSerializer,
    # cloud
    const.ApplicationTypeChoices.k8s.value: application_type.K8SSerializer
}


def get_serializer_class_by_application_type(_application_type):
    return type_serializer_classes_mapping.get(_application_type)
