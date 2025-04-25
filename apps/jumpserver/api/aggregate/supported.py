# views.py

from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView

router = DefaultRouter()

BASE_URL = "http://localhost:8080"


class ResourceTypeResourceSerializer(serializers.Serializer):
    name = serializers.CharField()
    path = serializers.CharField()
    app = serializers.CharField()
    verbose_name = serializers.CharField()
    description = serializers.CharField()


class ResourceTypeListApi(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="get_supported_resources",
        operation_summary="Get-all-support-resources",
        operation_description="Get all support resources, name, path, verbose_name description",
        responses={200: ResourceTypeResourceSerializer(many=True)},  # Specify the response serializer
    )
    def get(self, request):
        result = []
        resource_map = get_full_resource_map()
        for name, desc in resource_map.items():
            desc = resource_map.get(name, {})
            resource = {
                "name": name,
                **desc,
                "path": f'/api/v1/resources/{name}/',
            }
            result.append(resource)
        return Response(result)
