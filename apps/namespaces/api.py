from rest_framework.viewsets import ModelViewSet

from common.permissions import RBACPermission
from rbac.models import RoleBinding
from namespaces.models import Namespace
from namespaces.serializers import NamespaceSerializer


class NamespaceViewSet(ModelViewSet):

    permission_classes = (RBACPermission,)

    filter_fields = ('name',)
    search_fields = filter_fields
    ordering_fields = ('name', 'date_created')

    model = Namespace
    queryset = Namespace.objects.all()
    serializer_class = NamespaceSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_build_in:
            return self.filter_queryset(self.get_queryset())
        namespace_ids = RoleBinding.objects.filter(user=user).values_list('namespaces').distinct()
        return self.filter_queryset(self.get_queryset()).filter(id__in=namespace_ids)
