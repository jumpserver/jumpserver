import re

from django.apps import apps
from django.conf import settings
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.generators import SchemaGenerator

from rbac.permissions import RBACPermission


CHAT_AI_PERMISSIONS_UNSET = object()


class CustomSchemaGenerator(SchemaGenerator):
    from_mcp = False

    def get_schema(self, request=None, public=False):
        self.from_mcp = bool(
            request and (
                request.query_params.get('mcp') or
                request.path.endswith('swagger.json')
            )
        )
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

    def get_chat_ai_permission_metadata(self):
        """Return the statically resolvable RBAC requirements for this action.

        Chat AI must not guess permissions from an HTTP method or model name. A
        view-provided ``get_rbac_perms`` can depend on request data, path
        parameters, or the target object, so those operations are deliberately
        marked dynamic and excluded from Chat AI discovery.
        """
        explicit_permissions = getattr(
            self.view, 'chat_ai_required_permissions', CHAT_AI_PERMISSIONS_UNSET
        )
        if explicit_permissions is not CHAT_AI_PERMISSIONS_UNSET:
            if isinstance(explicit_permissions, str):
                explicit_permissions = (explicit_permissions,)
            elif not isinstance(
                explicit_permissions, (list, tuple, set, frozenset)
            ):
                return (), True
            if any(
                not isinstance(item, str) or not item
                for item in explicit_permissions
            ):
                return (), True
            return tuple(sorted(set(explicit_permissions))), False

        if callable(getattr(self.view, 'get_rbac_perms', None)):
            return (), True

        permission_classes = getattr(self.view, 'permission_classes', ()) or ()
        rbac_permission_classes = []
        for permission_class in permission_classes:
            try:
                if isinstance(permission_class, type) and issubclass(
                    permission_class, RBACPermission
                ):
                    rbac_permission_classes.append(permission_class)
            except TypeError:
                continue

        if not rbac_permission_classes:
            return (), True

        permissions = set()
        try:
            for permission_class in rbac_permission_classes:
                required = permission_class().get_require_perms(
                    self.view.request, self.view
                )
                if isinstance(required, str):
                    required = (required,)
                elif not isinstance(required, (list, tuple, set, frozenset)):
                    return (), True
                if any(not isinstance(item, str) or not item for item in required):
                    return (), True
                permissions.update(required)
        except Exception:
            return (), True
        return tuple(sorted(permissions)), False

    def get_description(self):
        description = super().get_description()
        base_dir = str(settings.BASE_DIR)
        my_apps = [
            app.label for app in apps.get_app_configs()
            if app.module.__file__ and app.module.__file__.startswith(base_dir)
        ]
        view_app = str(self.view.__class__.__module__.split('.')[0])
        if view_app in my_apps:
            # 内部 app 的 view 注释不展示在文档里
            return ''
        else:
            return description

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
                'service-access-logs', 'super-connection-tokens', 'flows',
                'apply-assets', 'apply-nodes', 'login-acls', 'login-asset-acls', 'command-filter-acls',
                'clipboard-acls', 'command-groups', 'connect-method-acls', 'system-msg-subscriptions', 'roles', 'role-bindings',
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
        required_permissions, permission_dynamic = self.get_chat_ai_permission_metadata()
        operation['x-jms-required-permissions'] = list(required_permissions)
        operation['x-jms-permission-dynamic'] = permission_dynamic
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
        return self.target.get_schema()


class LabeledChoiceFieldExtension(OpenApiSerializerFieldExtension):
    """
    为 LabeledChoiceField 提供 OpenAPI schema
    """
    target_class = LabeledChoiceField

    def map_serializer_field(self, auto_schema, direction):
        field = self.target
        description = getattr(field, 'help_text', '') or ''
        title = getattr(field, 'label', '') or ''
        
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
                'description': description,
                'title': title,
            }
        else:
            return {
                'type': 'object',
                'properties': {
                    'value': {'type': 'string'},
                    'label': {'type': 'string'}
                },
                'description': description,
                'title': title,
            }


class BitChoicesFieldExtension(OpenApiSerializerFieldExtension):
    """
    为 BitChoicesField 提供 OpenAPI schema
    """
    target_class = BitChoicesField

    def map_serializer_field(self, auto_schema, direction):
        field = self.target
        description = getattr(field, 'help_text', '') or ''
        title = getattr(field, 'label', '') or ''
        
        return {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'value': {'type': 'string'},
                    'label': {'type': 'string'}
                }
            },
            'description': description,
            'title': title,
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
            'description': getattr(field, 'help_text', '') or 'Label information',
            'title': getattr(field, 'label', '') or 'Label',
        }
