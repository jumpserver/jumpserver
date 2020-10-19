from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from rbac.models import RoleBinding
from common.permissions import RBACPermission
from common.drf.api import JMSModelViewSet
from .models import Account, AccountType, PropField
from .serializers import AccountSerializer, \
                         AccountTypeSerializer, \
                         AccountWithSecretSerializer, \
                         PropFieldSerializer


class AccountViewSet(JMSModelViewSet):
    permission_classes = (RBACPermission,)
    extra_action_perms_map = {
        'gain_secret': ['gain_secret'],
        'connect': ['connect'],
    }
    filter_fields = ('name', 'username', 'address', 'namespace__name')
    search_fields = filter_fields
    ordering_fields = ('username', 'address', 'namespace__name', 'date_created')

    model = Account
    queryset = Account.objects.all()
    serializer_classes = {
        'default': AccountSerializer,
        'gain_secret': AccountWithSecretSerializer,
        'connect': AccountWithSecretSerializer,
    }

    def get_queryset(self):
        user = self.request.user
        if user.is_build_in:
            return self.filter_queryset(self.queryset)
        namespace_ids = RoleBinding.objects.filter(user=user).values_list('namespaces').distinct()
        return self.filter_queryset(self.queryset).filter(namespace_id__in=namespace_ids)

    @action(methods=['get'], detail=True,  url_path='gain-secret')
    def gain_secret(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer_class()(instance)
        return Response(serializer.data)

    @action(methods=['get'], detail=True, url_path='connect')
    def connect(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer_class()(instance)
        return Response(serializer.data)


class AccountTypeViewSet(ModelViewSet):
    permission_classes = (RBACPermission,)
    filter_fields = ('name', 'category')
    search_fields = filter_fields
    ordering_fields = ('name', 'category', 'date_created')

    model = AccountType
    queryset = AccountType.objects.all()
    serializer_class = AccountTypeSerializer


class PropFieldViewSet(mixins.ListModelMixin,
                       GenericViewSet):
    permission_classes = (IsAuthenticated,)

    model = PropField
    queryset = PropField.objects.all()
    serializer_class = PropFieldSerializer
