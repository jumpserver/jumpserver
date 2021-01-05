from rest_framework import serializers
from applications import const
from . import application_category, application_type


__all__ = [
    'attrs_field_dynamic_mapping_serializers',
    'get_serializer_class_by_application_type',
]


# application category
# --------------------

category_db = const.ApplicationCategoryChoices.db.value
category_remote_app = const.ApplicationCategoryChoices.remote_app.value
category_cloud = const.ApplicationCategoryChoices.cloud.value


# application type
# ----------------

# db
type_mysql = const.ApplicationTypeChoices.mysql.value
type_mariadb = const.ApplicationTypeChoices.mariadb.value
type_oracle = const.ApplicationTypeChoices.oracle.value
type_pgsql = const.ApplicationTypeChoices.pgsql.value
# remote-app
type_chrome = const.ApplicationTypeChoices.chrome.value
type_mysql_workbench = const.ApplicationTypeChoices.mysql_workbench.value
type_vmware_client = const.ApplicationTypeChoices.vmware_client.value
type_custom = const.ApplicationTypeChoices.custom.value
# cloud
type_k8s = const.ApplicationTypeChoices.k8s.value


# define `attrs` field `dynamic mapping serializers`
# --------------------------------------------------


attrs_field_dynamic_mapping_serializers = {
    'default': serializers.Serializer,
    'category': {
        category_db: application_category.DBSerializer,
        category_remote_app: application_category.RemoteAppSerializer,
        category_cloud: application_category.CloudSerializer,
    },
    'type': {
        # db
        type_mysql: application_type.MySQLSerializer,
        type_mariadb: application_type.MariaDBSerializer,
        type_oracle: application_type.OracleSerializer,
        type_pgsql: application_type.PostgreSerializer,
        # remote-app
        type_chrome: application_type.ChromeSerializer,
        type_mysql_workbench: application_type.MySQLWorkbenchSerializer,
        type_vmware_client: application_type.VMwareClientSerializer,
        type_custom: application_type.CustomSerializer,
        # cloud
        type_k8s: application_type.K8SSerializer
    }
}


def get_serializer_class_by_application_type(_application_type):
    return attrs_field_dynamic_mapping_serializers['type'].get(_application_type)
