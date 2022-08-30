from rest_framework.decorators import action
from rest_framework.response import Response

from common.drf.api import JMSModelViewSet
from common.drf.serializers import GroupedChoiceSerailizer
from assets.models import Platform
from assets.serializers import PlatformSerializer, PlatformOpsMethodSerializer
from assets.const import AllTypes, Category
from assets.playbooks.platform import filter_platform_methods


__all__ = ['AssetPlatformViewSet']


class AssetPlatformViewSet(JMSModelViewSet):
    queryset = Platform.objects.all()
    serializer_classes = {
        'default': PlatformSerializer,
        'categories': GroupedChoiceSerailizer
    }
    filterset_fields = ['name', 'category', 'type']
    search_fields = ['name']
    rbac_perms = {
        'categories': 'assets.view_platform',
        'type_constraints': 'assets.view_platform',
        'ops_methods': 'assets.view_platform'
    }

    @action(methods=['GET'], detail=False)
    def categories(self, request, *args, **kwargs):
        data = AllTypes.grouped_choices_to_objs()
        serializer = self.get_serializer(data, many=True)
        return Response(serializer.data)

    @action(methods=['GET'], detail=False, url_path='type-constraints')
    def type_constraints(self, request, *args, **kwargs):
        category = request.query_params.get('category')
        tp = request.query_params.get('type')
        limits = AllTypes.get_constraints(category, tp)
        return Response(limits)

    @action(methods=['GET'], detail=False, url_path='ops-methods')
    def ops_methods(self, request, *args, **kwargs):
        category = request.query_params.get('category')
        tp = request.query_params.get('type')
        method = request.query_params.get('method')
        methods = filter_platform_methods(category, tp, method)
        serializer = PlatformOpsMethodSerializer(methods, many=True)
        return Response(serializer.data)

    def check_object_permissions(self, request, obj):
        if request.method.lower() in ['delete', 'put', 'patch'] and obj.internal:
            self.permission_denied(
                request, message={"detail": "Internal platform"}
            )
        return super().check_object_permissions(request, obj)
