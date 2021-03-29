from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, CreateModelMixin, DestroyModelMixin
from common.permissions import IsOrgAdmin
from ..models import SafeRoleBinding
from .. import serializers


__all__ = ['SafeRoleBindingViewSet']


class SafeRoleBindingViewSet(ListModelMixin, CreateModelMixin, DestroyModelMixin, GenericViewSet):
    permission_classes = (IsOrgAdmin, )
    filterset_fields = ('user', 'safe', 'role')
    search_fields = ('user__username', )
    serializer_class = serializers.SafeRoleBindingSerializer
    queryset = SafeRoleBinding.objects.all()

