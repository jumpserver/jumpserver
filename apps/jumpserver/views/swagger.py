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
            '/move-to-assets/', 'dashboard',

        ]
        for p in excludes:
            if path.find(p) >= 0:
                return True
        return False

    def exclude_some_app(self, path):
        parts = path.split('/')
        if len(parts) < 4:
            return False

        apps = []
        if self.from_mcp:
            apps = [
                'ops', 'tickets', 'common', 'authentication',
                'settings', 'xpack', 'terminal', 'rbac'
            ]

        app_name = parts[3]
        if app_name in apps:
            return True
        return False

    def get_operation(self, view, path, prefix, method, components, request):
        # 这里可以对 path 进行处理
        if self.exclude_some_paths(path):
            return None
        if self.exclude_some_app(path):
            return None
        operation = super().get_operation(view, path, prefix, method, components, request)
        operation_id = operation.get('operationId')
        if 'bulk' in operation_id:
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


def get_swagger_view(with_auth=True):
    from ..urls import api_v1
    from django.urls import path, include
    patterns = [
        path('api/v1/', include(api_v1))
    ]

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
