from drf_yasg.inspectors import SwaggerAutoSchema

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys):
        if len(operation_keys) > 2:
            return [operation_keys[0] + '_' + operation_keys[1]]
        return super().get_tags(operation_keys)

    def get_operation(self, operation_keys):
        operation = super().get_operation(operation_keys)
        operation.summary = operation.operation_id
        return operation


def get_swagger_view(version='v1'):
    from .urls import api_v1_patterns, api_v2_patterns
    if version == "v2":
        patterns = api_v2_patterns
    else:
        patterns = api_v1_patterns
    schema_view = get_schema_view(
        openapi.Info(
            title="Jumpserver API Docs",
            default_version=version,
            description="Jumpserver Restful api docs",
            terms_of_service="https://www.jumpserver.org",
            contact=openapi.Contact(email="support@fit2cloud.com"),
            license=openapi.License(name="GPLv2 License"),
        ),
        public=True,
        patterns=patterns,
        permission_classes=(permissions.AllowAny,),
    )
    return schema_view

