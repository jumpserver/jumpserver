import re

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.generators import SchemaGenerator

__all__ = [
    'CustomSchemaGenerator', 'CustomAutoSchema'
]


class CustomSchemaGenerator(SchemaGenerator):
    from_mcp = False

    def get_schema(self, request=None, public=False):
        self.from_mcp = request.query_params.get('mcp') or request.path.endswith('swagger.json')
        return super().get_schema(request, public)


class CustomAutoSchema(AutoSchema):
    def __init__(self, *args, **kwargs):
        self.from_mcp = True
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
            'profile/permissions', 'prometheus', 'constraints',
            '/api/swagger.json', '/api/swagger.yaml', 
        ]
        for p in excludes:
            if path.find(p) >= 0:
                return True
        return False

    def exclude_some_models(self, model):
        models = []
        if self.from_mcp:
            models = [
                'users', 'user-groups', 
                'assets', 'hosts', 'devices', 'databases',
                'webs', 'clouds', 'ds', 'platforms', 
                'nodes', 'zones', 'labels', 
                'accounts', 'account-templates',
                'asset-permissions',
            ]
        if models and model in models:
            return False
        return True

    def exclude_some_apps(self, app):
        apps = []
        if self.from_mcp:
            apps = [
                'users', 'assets', 'accounts',
                'perms', 'labels',
            ]
        if apps and app in apps:
            return False        
        return True

    def exclude_some_app_model(self, path):
        parts = path.split('/')
        if len(parts) < 5 :
            return True

        if len(parts) == 7 and parts[5] != "{id}":
            return True
        
        if len(parts) > 7:
            return True

        app_name = parts[3]
        if self.exclude_some_apps(app_name):
            return True

        if self.exclude_some_models(parts[4]):
            return True
        return False

    def is_excluded(self):
        if self.exclude_some_paths(self.path):
            return True
        
        if self.exclude_some_app_model(self.path):
            return True
        return False

    def exclude_some_operations(self, operation_id):
        exclude_operations = [
            'orgs_orgs_read', 'orgs_orgs_update', 'orgs_orgs_delete', 
            'orgs_orgs_create', 'orgs_orgs_partial_update',
        ]
        if operation_id in exclude_operations:
            return True

        if 'bulk' in operation_id:
            return True

        if 'destroy' in operation_id:
            return True

        if 'update' in operation_id and 'partial' not in operation_id:
            return True

        return False

    def get_operation(self, path, *args, **kwargs):
        operation = super().get_operation(path, *args, **kwargs)
        if not operation:
            return operation

        operation_id = operation.get('operationId')
        if self.exclude_some_operations(operation_id):
            return None

        if not operation.get('summary', ''):
            operation['summary'] = operation.get('operationId')
        
        # if self.is_excluded():
        #     return None

        return operation
