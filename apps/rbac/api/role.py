from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _

from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from ..models import Role, NamespaceRoleBinding, OrgRoleBinding
from rbac.permissions import IsSystemAdminUser
from ..serializers import RoleSerializer, NamespaceRoleBindingSerializer, OrgRoleBindingSerializer

__all__ = ['RoleViewSet', 'NamespaceRoleBindingViewSet', 'OrgRoleBindingViewSet']


class RoleViewSet(ModelViewSet):
    permission_classes = (IsSystemAdminUser,)
    filter_fields = ('name', 'type')
    search_fields = filter_fields
    ordering_fields = ('type',)
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class NamespaceRoleBindingViewSet(mixins.CreateModelMixin,
                                  mixins.ListModelMixin,
                                  GenericViewSet):
    permission_classes = (IsSystemAdminUser,)
    filter_fields = ('user', 'namespace_id')
    queryset = NamespaceRoleBinding.objects.all()
    serializer_class = NamespaceRoleBindingSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs, many=True)

    @action(methods=['delete'], detail=False,  url_path='delete_user')
    def delete_user(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id')
        namespace_id = request.query_params.get('namespace_id')
        obj = get_object_or_404(self.get_queryset(), user_id=user_id, namespace_id=namespace_id)
        obj.delete()
        return Response({'msg': _('Delete success')}, status=status.HTTP_200_OK)


class OrgRoleBindingViewSet(mixins.CreateModelMixin,
                            mixins.ListModelMixin,
                            GenericViewSet):
    permission_classes = (IsSystemAdminUser,)
    filter_fields = ('user', 'org_id')
    queryset = OrgRoleBinding.objects.all()

    serializer_class = OrgRoleBindingSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs, many=True)

    @action(methods=['delete'], detail=False,  url_path='delete_user')
    def delete_user(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id')
        org_id = request.query_params.get('org_id')
        obj = get_object_or_404(self.get_queryset(), user_id=user_id, org_id=org_id)
        obj.delete()
        return Response({'msg': _('Delete success')}, status=status.HTTP_200_OK)
