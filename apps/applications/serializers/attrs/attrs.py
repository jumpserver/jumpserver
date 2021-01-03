import copy
from applications import const
from common.drf.fields import IgnoreSensitiveInfoReadOnlyJSONField
from . import category, type as application_type


__all__ = [
    'get_attrs_field_dynamic_mapping_rules', 'get_attrs_field_mapping_rule_by_view',
    'get_serializer_by_application_type',
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


# define `attrs` field `DynamicMappingField` mapping_rules
# -----------------------------------------------------


__ATTRS_FIELD_DYNAMIC_MAPPING_RULES = {
    'default': IgnoreSensitiveInfoReadOnlyJSONField,
    'category': {
        category_db: category.DBSerializer,
        category_remote_app: category.RemoteAppSerializer,
        category_cloud: category.CloudSerializer,
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


# Note:
# The dynamic mapping rules of `attrs` field is obtained
# through call method `get_attrs_field_dynamic_mapping_rules`

def get_attrs_field_dynamic_mapping_rules():
    return copy.deepcopy(__ATTRS_FIELD_DYNAMIC_MAPPING_RULES)


# get `attrs dynamic field` mapping rule by `view object`
# ----------------------------------------------------


def get_attrs_field_mapping_rule_by_view(view):
    query_type = view.request.query_params.get('type')
    query_category = view.request.query_params.get('category')
    if query_type:
        mapping_rule = ['type', query_type]
    elif query_category:
        mapping_rule = ['category', query_category]
    else:
        mapping_rule = ['default']
    return mapping_rule


# get `category` mapping `serializer`
# -----------------------------------

def get_serializer_by_application_type(app_tp):
    return __ATTRS_FIELD_DYNAMIC_MAPPING_RULES['type'].get(app_tp)
