from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework import mixins

from accounts.api import CsrfExemptSessionAuthentication
from rbac.serializers import PermissionSerializer, ContentTypeSerializer


__all__ = ['PermissionViewSet', 'ContentTypeViewSet']


class PermissionViewSet(mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.UpdateModelMixin,
                        mixins.DestroyModelMixin,
                        mixins.ListModelMixin,
                        GenericViewSet):

    permission_classes = (IsAuthenticated,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    filter_fields = ('name', 'codename')
    search_fields = filter_fields
    ordering_fields = ('name', 'codename')

    model = Permission
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class ContentTypeViewSet(mixins.ListModelMixin,
                         GenericViewSet):

    permission_classes = (IsAuthenticated,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    search_fields = ('app_label', 'model')

    model = ContentType
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializer
