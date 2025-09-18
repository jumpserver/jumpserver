# views.py

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .const import common_params
from .proxy import ProxyMixin
from .utils import param_dic_to_param

one_param = [
    {
        'name': 'id',
        'in': 'path',
        'required': True,
        'description': 'Resource ID',
        'type': 'string',
    }
]

object_params = [
    param_dic_to_param(d)
    for d in common_params + one_param
]


class ResourceDetailApi(ProxyMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_resource_detail",
        summary="Get resource detail",
        parameters=object_params,
        description="""
        Get resource detail. 
         {resource} is the resource name, GET /api/v1/resources/ to get full supported resource.
        """,
    )
    def get(self, request, resource, pk=None):
        return self._proxy(request, resource, pk=pk, action='retrieve')

    @extend_schema(
        operation_id="delete_resource",
        summary="Delete the resource",
        parameters=object_params,
        description="Delete the resource, and can not be restored",
    )
    def delete(self, request, resource, pk=None):
        return self._proxy(request, resource, pk, action='destroy')

    @extend_schema(
        operation_id="update_resource",
        summary="Update the resource property",
        parameters=object_params,
        description="""
        Update the resource property, all property will be update,
         {resource} is the resource name, GET /api/v1/resources/ to get full supported resource.

        OPTION /api/v1/resources/{resource}/{id}/?action=put to get field type and helptext.
        """,
    )
    def put(self, request, resource, pk=None):
        return self._proxy(request, resource, pk, action='update')

    @extend_schema(
        operation_id="partial_update_resource",
        summary="Update the resource property",
        parameters=object_params,
        description="""
        Partial update the resource property, only request property will be update,
        OPTION /api/v1/resources/{resource}/{id}/?action=patch to get field type and helptext.
        """,
    )
    def patch(self, request, resource, pk=None):
        return self._proxy(request, resource, pk, action='partial_update')
