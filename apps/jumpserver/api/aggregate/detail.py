# views.py

from drf_yasg.utils import swagger_auto_schema
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

    @swagger_auto_schema(
        operation_id="get_resource_detail",
        operation_summary="Get resource detail",
        manual_parameters=object_params,
        operation_description="""
        Get resource detail. 
         {resource} is the resource name, GET /api/v1/resources/ to get full supported resource.

    """, )
    def get(self, request, resource, pk=None):
        return self._proxy(request, resource, pk=pk, action='retrieve')

    @swagger_auto_schema(
        operation_id="delete_resource",
        operation_summary="Delete the resource ",
        manual_parameters=object_params,
        operation_description="Delete the resource, and can not be restored",
    )
    def delete(self, request, resource, pk=None):
        return self._proxy(request, resource, pk, action='destroy')

    @swagger_auto_schema(
        operation_id="update_resource",
        operation_summary="Update the resource property",
        manual_parameters=object_params,
        operation_description="""
        Update the resource property, all property will be update,
         {resource} is the resource name, GET /api/v1/resources/ to get full supported resource.

        OPTION /api/v1/resources/{resource}/{id}/?action=put to get field type and helptext.
    """)
    def put(self, request, resource, pk=None):
        return self._proxy(request, resource, pk, action='update')

    @swagger_auto_schema(
        operation_id="partial_update_resource",
        operation_summary="Update the resource property",
        manual_parameters=object_params,
        operation_description="""
        Partial update the resource property, only request property will be update,
        OPTION /api/v1/resources/{resource}/{id}/?action=patch to get field type and helptext.
    """)
    def patch(self, request, resource, pk=None):
        return self._proxy(request, resource, pk, action='partial_update')
