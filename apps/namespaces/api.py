from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from accounts.api import CsrfExemptSessionAuthentication
from rbac.models import RoleBinding
from namespaces.models import Namespace
from namespaces.serializers import NamespaceSerializer


class NamespaceViewSet(mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin,
                       mixins.ListModelMixin,
                       GenericViewSet):

    permission_classes = (IsAuthenticated,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    filter_fields = ('name',)
    search_fields = filter_fields
    ordering_fields = ('name', 'date_created')

    model = Namespace
    queryset = Namespace.objects.all()
    serializer_class = NamespaceSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_build_in:
            return self.filter_queryset(self.queryset)
        namespace_ids = RoleBinding.objects.filter(user=user).values_list('namespaces').distinct()
        return self.filter_queryset(self.queryset).filter(id__in=namespace_ids)
