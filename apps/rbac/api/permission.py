
from common.drf.api import JMSModelViewSet
from common.permissions import IsOrgAdmin, IsValidUser
from ..models import Permission, RoleBinding
from ..serializers import PermissionSerializer, UserPermsSerializer

__all__ = ['PermissionViewSet']


class PermissionViewSet(JMSModelViewSet):
    filterset_fields = ['codename']
    serializer_class = PermissionSerializer
    permission_classes = (IsOrgAdmin, )

    def get_queryset(self):
        scope = self.request.query_params.get('scope') or 'org'
        queryset = Permission.get_permissions(scope)\
            .prefetch_related('content_type')
        return queryset


# class UserPermsApi(ListAPIView):
#     serializer_class = UserPermsSerializer
#     permission_classes = (IsValidUser,)
#
#     def list(self, request, *args, **kwargs):
#         perms = RoleBinding.get_user_perms(request.user)
#         serializer = super().get_serializer(data={'perms': perms})
#         return Res

