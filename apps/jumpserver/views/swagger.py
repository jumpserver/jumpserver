import os

from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.views import get_schema_view
from rest_framework import permissions


class CustomSchemaGenerator(OpenAPISchemaGenerator):
    from_mcp = False

    def get_schema(self, request=None, public=False):
        self.from_mcp = request.query_params.get('mcp') or request.path.endswith('swagger.json')
        return super().get_schema(request, public)

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

    def get_operation(self, view, path, prefix, method, components, request):
        # 这里可以对 path 进行处理
        if self.exclude_some_paths(path):
            return None
        if self.exclude_some_app_model(path):
            return None
        operation = super().get_operation(view, path, prefix, method, components, request)
        operation_id = operation.get('operationId')
        if 'bulk' in operation_id:
            return None
        exclude_operations = [
            'orgs_orgs_read', 'orgs_orgs_update', 'orgs_orgs_delete', 'orgs_orgs_create',
            'orgs_orgs_partial_update',
        ]
        if operation_id in exclude_operations:
            return None
        return operation


class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys):
        if len(operation_keys) > 2:
            return [operation_keys[0] + '_' + operation_keys[1]]
        return super().get_tags(operation_keys)

    def get_operation_id(self, operation_keys):
        action = ''
        dump_keys = [k for k in operation_keys]
        if hasattr(self.view, 'action'):
            action = self.view.action
            if action == "bulk_destroy":
                action = "bulk_delete"
        if dump_keys[-2] == "children":
            if self.path.find('id') < 0:
                dump_keys.insert(-2, "root")
        if dump_keys[0] == "perms" and dump_keys[1] == "users":
            if self.path.find('{id}') < 0:
                dump_keys.insert(2, "my")
        if action.replace('bulk_', '') == dump_keys[-1]:
            dump_keys[-1] = action
        return super().get_operation_id(tuple(dump_keys))

    def get_operation(self, operation_keys):
        operation = super().get_operation(operation_keys)
        if not getattr(operation, 'summary', ''):
            operation.summary = operation.operation_id
        return operation

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
            fields += self.probe_inspectors(self.filter_inspectors, 'get_filter_parameters', filter_backend()) or []
        return fields


api_info = openapi.Info(
    title="JumpServer API Docs",
    default_version='v1',
    description="JumpServer Restful api docs",
    terms_of_service="https://www.jumpserver.com",
    contact=openapi.Contact(email="support@lxware.hk"),
    license=openapi.License(name="GPLv3 License"),
)


def get_swagger_view():
    from ..urls import api_v1
    from django.urls import path, include
    patterns = [
        path('api/v1/', include(api_v1))
    ]

    with_auth = os.environ.get('DOC_AUTH', '1') == '1'
    if with_auth:
        permission_classes = (permissions.IsAuthenticated,)
        public = False
    else:
        permission_classes = []
        public = True

    schema_view = get_schema_view(
        api_info,
        public=public,
        patterns=patterns,
        generator_class=CustomSchemaGenerator,
        permission_classes=permission_classes
    )
    return schema_view
