from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework import mixins

from rbac.serializers import PermissionSerializer, ContentTypeSerializer
from .. import utils


__all__ = ['PermissionViewSet', 'ContentTypeViewSet']


class PermissionViewSet(ModelViewSet):

    permission_classes = (IsAuthenticated,)

    filter_fields = ('name', 'codename')
    search_fields = filter_fields
    ordering_fields = ('name', 'codename')

    model = Permission
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.queryset)
        result = utils.group_permissions(queryset)
        return Response(result)


class ContentTypeViewSet(mixins.ListModelMixin,
                         GenericViewSet):

    permission_classes = (IsAuthenticated,)

    search_fields = ('app_label', 'model')

    model = ContentType
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.queryset)
        result = utils.group_content_types(queryset)
        return Response(result)
