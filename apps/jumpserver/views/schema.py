import re

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.generators import SchemaGenerator


class CustomSchemaGenerator(SchemaGenerator):
    from_mcp = False

    def get_schema(self, request=None, public=False):
        self.from_mcp = request.query_params.get('mcp') or request.path.endswith('swagger.json')
        return super().get_schema(request, public)


class CustomAutoSchema(AutoSchema):
    def __init__(self, *args, **kwargs):
        self.from_mcp = kwargs.get('from_mcp', False)
        super().__init__(*args, **kwargs)

    def map_parsers(self):
        return ['application/json']

    def map_renderers(self, *args, **kwargs):
        return ['application/json']

    def get_tags(self):
        operation_keys = self._tokenize_path()
        if len(operation_keys) == 1:
            return []
        tags = ['_'.join(operation_keys[:2])]
        return tags
   
    def get_operation(self, path, *args, **kwargs):
        if path.endswith('render-to-json/'):
            return None
        # if not path.startswith('/api/v1/users'):
            # return None
        operation = super().get_operation(path, *args, **kwargs)
        if not operation:
            return operation

        if not operation.get('summary', ''):
            operation['summary'] = operation.get('operationId')

        return operation

    def get_operation_id(self):
        tokenized_path = self._tokenize_path()
        # replace dashes as they can be problematic later in code generation
        tokenized_path = [t.replace('-', '_') for t in tokenized_path]

        action = ''
        if hasattr(self.view, 'action'):
            action = self.view.action

        if not action:
            if self.method == 'GET' and self._is_list_view():
                action = 'list'
            else:
                action = self.method_mapping[self.method.lower()]

        if action == "bulk_destroy":
            action = "bulk_delete"

        if not tokenized_path:
            tokenized_path.append('root')

        if re.search(r'<drf_format_suffix\w*:\w+>', self.path_regex):
            tokenized_path.append('formatted')

        return '_'.join(tokenized_path + [action])

    def get_filter_parameters(self):
        if not self.should_filter():
            return []

        fields = []
        if hasattr(self.view, 'get_filter_backends'):
            backends = self.view.get_filter_backends()
        elif hasattr(self.view, 'filter_backends'):
            backends = self.view.filter_backends
        else:
            backends = []
        for filter_backend in backends:
            fields += self.probe_inspectors(
                self.filter_inspectors, 'get_filter_parameters', filter_backend()
            ) or []
        return fields

    def get_auth(self):
        return [{'Bearer': []}]

    def get_operation_security(self):
        """
        重写操作安全配置，统一使用 Bearer token
        """
        return [{'Bearer': []}]

    def get_components_security_schemes(self):
        """
        重写安全方案定义，避免认证类解析错误
        """
        return {
            'Bearer': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'JWT token for API authentication'
            }
        }

    @staticmethod
    def exclude_some_paths(path):
        # 这里可以对 paths 进行处理
        excludes = [
            '/report/', '/render-to-json/', '/suggestions/',
            'executions', 'automations', 'change-secret-records',
            'change-secret-dashboard', '/copy-to-assets/',
            '/move-to-assets/', 'dashboard', 'index', 'countries',
            '/resources/cache/', 'profile/mfa', 'profile/password',
            'profile/permissions', 'prometheus', 'constraints'
        ]
        for p in excludes:
            if path.find(p) >= 0:
                return True
        return False

    def exclude_some_app_model(self, path):
        parts = path.split('/')
        if len(parts) < 5:
            return False

        apps = []
        if self.from_mcp:
            apps = [
                'ops', 'tickets', 'authentication',
                'settings', 'xpack', 'terminal', 'rbac',
                'notifications', 'promethues', 'acls'
            ]

        app_name = parts[3]
        if app_name in apps:
            return True
        models = []
        model = parts[4]
        if self.from_mcp:
            models = [
                'users', 'user-groups', 'users-groups-relations', 'assets', 'hosts', 'devices', 'databases',
                'webs', 'clouds', 'gpts', 'ds', 'customs', 'platforms', 'nodes', 'zones', 'gateways',
                'protocol-settings', 'labels', 'virtual-accounts', 'gathered-accounts', 'account-templates',
                'account-template-secrets', 'account-backups', 'account-backup-executions',
                'change-secret-automations', 'change-secret-executions', 'change-secret-records',
                'gather-account-automations', 'gather-account-executions', 'push-account-automations',
                'push-account-executions', 'push-account-records', 'check-account-automations',
                'check-account-executions', 'account-risks', 'integration-apps', 'asset-permissions',
                'asset-permissions-users-relations', 'asset-permissions-user-groups-relations',
                'asset-permissions-assets-relations', 'asset-permissions-nodes-relations', 'terminal-status',
                'terminals', 'tasks', 'status', 'replay-storages', 'command-storages', 'session-sharing-records',
                'endpoints', 'endpoint-rules', 'applets', 'applet-hosts', 'applet-publications',
                'applet-host-deployments', 'virtual-apps', 'app-providers', 'virtual-app-publications',
                'celery-period-tasks', 'task-executions', 'adhocs', 'playbooks', 'variables', 'ftp-logs',
                'login-logs', 'operate-logs', 'password-change-logs', 'job-logs', 'jobs', 'user-sessions',
                'service-access-logs', 'chatai-prompts', 'super-connection-tokens', 'flows',
                'apply-assets', 'apply-nodes', 'login-acls', 'login-asset-acls', 'command-filter-acls',
                'command-groups', 'connect-method-acls', 'system-msg-subscriptions', 'roles', 'role-bindings',
                'system-roles', 'system-role-bindings', 'org-roles', 'org-role-bindings', 'content-types',
                'labeled-resources', 'account-backup-plans', 'account-check-engines', 'account-secrets',
                'change-secret', 'integration-applications', 'push-account', 'directories', 'connection-token',
                'groups', 'accounts', 'resource-types', 'favorite-assets', 'activities', 'platform-automation-methods',
            ]
        if model in models:
            return True
        return False

    def is_excluded(self):
        if self.exclude_some_paths(self.path):
            return True
        if self.exclude_some_app_model(self.path):
            return True
        return False

    def get_operation(self, path, *args, **kwargs):
        operation = super().get_operation(path, *args, **kwargs)
        if not operation:
            return operation

        operation_id = operation.get('operationId')
        if 'bulk' in operation_id:
            return None

        if not operation.get('summary', ''):
            operation['summary'] = operation.get('operationId')

        exclude_operations = [
            'orgs_orgs_read', 'orgs_orgs_update', 'orgs_orgs_delete', 
            'orgs_orgs_create', 'orgs_orgs_partial_update',
        ]
        if operation_id in exclude_operations:
            return None
        return operation

# 添加自定义字段的 OpenAPI 扩展
from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import build_basic_type
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField, BitChoicesField


class ObjectRelatedFieldExtension(OpenApiSerializerFieldExtension):
    """
    为 ObjectRelatedField 提供 OpenAPI schema
    """
    target_class = ObjectRelatedField

    def map_serializer_field(self, auto_schema, direction):
        field = self.target
        
        # 获取字段的基本信息
        field_type = 'array' if field.many else 'object'
        
        if field_type == 'array':
            # 如果是多对多关系
            return {
                'type': 'array',
                'items': self._get_openapi_item_schema(field),
                'description': getattr(field, 'help_text', ''),
                'title': getattr(field, 'label', ''),
            }
        else:
            # 如果是一对一关系
            return {
                'type': 'object',
                'properties': self._get_openapi_properties_schema(field),
                'description': getattr(field, 'help_text', ''),
                'title': getattr(field, 'label', ''),
            }

    def _get_openapi_item_schema(self, field):
        """
        获取数组项的 OpenAPI schema
        """
        return self._get_openapi_object_schema(field)

    def _get_openapi_object_schema(self, field):
        """
        获取对象的 OpenAPI schema
        """
        properties = {}
        
        # 动态分析 attrs 中的属性类型
        for attr in field.attrs:
            # 尝试从 queryset 的 model 中获取字段信息
            field_type = self._infer_field_type(field, attr)
            properties[attr] = {
                'type': field_type,
                'description': f'{attr} field'
            }
        
        return {
            'type': 'object',
            'properties': properties,
            'required': ['id'] if 'id' in field.attrs else []
        }

    def _infer_field_type(self, field, attr_name):
        """
        智能推断字段类型
        """
        try:
            # 如果有 queryset，尝试从 model 中获取字段信息
            if hasattr(field, 'queryset') and field.queryset is not None:
                model = field.queryset.model
                if hasattr(model, '_meta') and hasattr(model._meta, 'fields'):
                    model_field = model._meta.get_field(attr_name)
                    if model_field:
                        return self._map_django_field_type(model_field)
        except Exception:
            pass
        
        # 如果没有 queryset 或无法获取字段信息，使用启发式规则
        return self._heuristic_field_type(attr_name)

    def _map_django_field_type(self, model_field):
        """
        将 Django 字段类型映射到 OpenAPI 类型
        """
        field_type = type(model_field).__name__
        
        # 整数类型
        if 'Integer' in field_type or 'BigInteger' in field_type or 'SmallInteger' in field_type:
            return 'integer'
        # 浮点数类型
        elif 'Float' in field_type or 'Decimal' in field_type:
            return 'number'
        # 布尔类型
        elif 'Boolean' in field_type:
            return 'boolean'
        # 日期时间类型
        elif 'DateTime' in field_type or 'Date' in field_type or 'Time' in field_type:
            return 'string'
        # 文件类型
        elif 'File' in field_type or 'Image' in field_type:
            return 'string'
        # 其他类型默认为字符串
        else:
            return 'string'

    def _heuristic_field_type(self, attr_name):
        """
        启发式推断字段类型
        """
        # 基于属性名的启发式规则
        
        if attr_name in ['is_active', 'enabled', 'visible'] or attr_name.startswith('is_'):
            return 'boolean'
        elif attr_name in ['count', 'number', 'size', 'amount']:
            return 'integer'
        elif attr_name in ['price', 'rate', 'percentage']:
            return 'number'
        else:
            # 默认返回字符串类型
            return 'string'

    def _get_openapi_properties_schema(self, field):
        """
        获取对象属性的 OpenAPI schema
        """
        return self._get_openapi_object_schema(field)['properties']


class LabeledChoiceFieldExtension(OpenApiSerializerFieldExtension):
    """
    为 LabeledChoiceField 提供 OpenAPI schema
    """
    target_class = LabeledChoiceField

    def map_serializer_field(self, auto_schema, direction):
        field = self.target
        
        if getattr(field, 'many', False):
            return {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'value': {'type': 'string'},
                        'label': {'type': 'string'}
                    }
                },
                'description': getattr(field, 'help_text', ''),
                'title': getattr(field, 'label', ''),
            }
        else:
            return {
                'type': 'object',
                'properties': {
                    'value': {'type': 'string'},
                    'label': {'type': 'string'}
                },
                'description': getattr(field, 'help_text', ''),
                'title': getattr(field, 'label', ''),
            }


class BitChoicesFieldExtension(OpenApiSerializerFieldExtension):
    """
    为 BitChoicesField 提供 OpenAPI schema
    """
    target_class = BitChoicesField

    def map_serializer_field(self, auto_schema, direction):
        field = self.target
        
        return {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'value': {'type': 'string'},
                    'label': {'type': 'string'}
                }
            },
            'description': getattr(field, 'help_text', ''),
            'title': getattr(field, 'label', ''),
        }


class LabelRelatedFieldExtension(OpenApiSerializerFieldExtension):
    """
    为 LabelRelatedField 提供 OpenAPI schema
    """
    target_class = 'common.serializers.fields.LabelRelatedField'

    def map_serializer_field(self, auto_schema, direction):
        field = self.target
        
        # LabelRelatedField 返回一个包含 id, name, value, color 的对象
        return {
            'type': 'object',
            'properties': {
                'id': {
                    'type': 'string',
                    'description': 'Label ID'
                },
                'name': {
                    'type': 'string',
                    'description': 'Label name'
                },
                'value': {
                    'type': 'string',
                    'description': 'Label value'
                },
                'color': {
                    'type': 'string',
                    'description': 'Label color'
                }
            },
            'required': ['id', 'name', 'value'],
            'description': getattr(field, 'help_text', 'Label information'),
            'title': getattr(field, 'label', 'Label'),
        }
