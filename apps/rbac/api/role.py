from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework import mixins

from accounts.api import CsrfExemptSessionAuthentication
from rbac.models import Role, RoleBinding
from rbac.serializers import RoleSerializer, RoleBindingSerializer


__all__ = ['RoleViewSet', 'RoleBindingViewSet']


class RoleViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  GenericViewSet):
    # TODO all permission_classes of view to be added
    permission_classes = (IsAuthenticated,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    filter_fields = ('name', 'type', 'is_build_in')
    search_fields = filter_fields
    ordering_fields = ('type',)

    model = Role
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class RoleBindingViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.DestroyModelMixin,
                         mixins.ListModelMixin,
                         GenericViewSet):

    permission_classes = (IsAuthenticated,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    filter_fields = ('user', 'role')
    search_fields = filter_fields
    ordering_fields = ('role',)

    model = RoleBinding
    queryset = RoleBinding.objects.all()
    serializer_class = RoleBindingSerializer
