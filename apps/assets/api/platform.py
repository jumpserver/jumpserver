from rest_framework.response import Response

from assets.const import AllTypes
from assets.models import Platform, PlatformAutomation
from assets.serializers import PlatformSerializer
from common.api import JMSModelViewSet
from common.serializers import GroupedChoiceSerializer
from orgs.mixins.generics import RetrieveUpdateAPIView

__all__ = ['AssetPlatformViewSet', 'PlatformAutomationParamsApi']


class AssetPlatformViewSet(JMSModelViewSet):
    queryset = Platform.objects.all()
    serializer_classes = {
        'default': PlatformSerializer,
        'categories': GroupedChoiceSerializer
    }
    filterset_fields = ['name', 'category', 'type']
    search_fields = ['name']
    rbac_perms = {
        'categories': 'assets.view_platform',
        'type_constraints': 'assets.view_platform',
        'ops_methods': 'assets.view_platform'
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(type__in=AllTypes.get_types())
        return queryset

    def get_object(self):
        pk = self.kwargs.get('pk', '')
        if pk.isnumeric():
            return super().get_object()
        return self.get_queryset().get(name=pk)

    def check_object_permissions(self, request, obj):
        if request.method.lower() in ['delete', 'put', 'patch'] and obj.internal:
            self.permission_denied(
                request, message={"detail": "Internal platform"}
            )
        return super().check_object_permissions(request, obj)


class PlatformAutomationParamsApi(RetrieveUpdateAPIView):
    instance = None
    model = PlatformAutomation

    @property
    def ansible_method_id(self):
        return self.kwargs.get('ansible_method_id')

    def get_serializer_class(self):
        return self.model.generate_params_serializer(self.instance, self.ansible_method_id)

    def get_object(self):
        self.instance = super().get_object()
        return self.instance

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = instance.params.get(self.ansible_method_id, {})
        serializer = self.get_serializer(data)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        instance.params.setdefault(self.ansible_method_id, {}).update(validated_data)
        instance.save(update_fields=['params'])
        return Response(status=200)
