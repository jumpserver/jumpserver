from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import ContentType
from rest_framework import viewsets
from common.permissions import IsSuperUser
from ..serializers import ContentTypeSerializer


__all__ = ['ContentTypeViewSet']


class ContentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsSuperUser, )
    filterset_fields = ['id', 'app_label', 'model']
    search_fields = filterset_fields
    serializer_class = ContentTypeSerializer
    queryset = ContentType.objects.all()


