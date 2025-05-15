# views.py

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView

from .const import list_params, common_params
from .proxy import ProxyMixin
from .utils import param_dic_to_param

router = DefaultRouter()

BASE_URL = "http://localhost:8080"

list_params = [
    param_dic_to_param(d)
    for d in list_params + common_params
]

create_params = [
    param_dic_to_param(d)
    for d in common_params
]

list_schema = {
    "required": [
        "count",
        "results"
    ],
    "type": "object",
    "properties": {
        "count": {
            "type": "integer"
        },
        "next": {
            "type": "string",
            "format": "uri",
            "x-nullable": True
        },
        "previous": {
            "type": "string",
            "format": "uri",
            "x-nullable": True
        },
        "results": {
            "type": "array",
            "items": {
            }
        }
    }
}

list_response = openapi.Response("Resource list response", schema=openapi.Schema(**list_schema))


class ResourceListApi(ProxyMixin, APIView):
    @swagger_auto_schema(
        operation_id="get_resource_list",
        operation_summary="Get resource list",
        manual_parameters=list_params,
        responses={200: list_response},
        operation_description="""
          Get resource list, you should set the resource name in the url.
          OPTIONS /api/v1/resources/{resource}/?action=get to get every type resource's field type and help text.
    """, )
    # ↓↓↓ Swagger 自动文档 ↓↓↓
    def get(self, request, resource):
        return self._proxy(request, resource)

    @swagger_auto_schema(
        operation_id="create_resource_by_type",
        operation_summary="Create resource",
        manual_parameters=create_params,
        operation_description="""
          Create resource, 
          OPTIONS /api/v1/resources/{resource}/?action=post to get every resource type field type and helptext, and 
          you will know how to create it.
      """)
    def post(self, request, resource, pk=None):
        if not resource:
            resource = request.data.pop('resource', '')
        return self._proxy(request, resource, pk, action='create')

    def options(self, request, resource, pk=None):
        return self._proxy(request, resource, pk, action='metadata')
