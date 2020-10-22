
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from common.permissions import IsSuperUser
from common.drf.api import JMSModelViewSet
from namespaces.permissions import NamespaceRBACPermission
from .models import Account, AccountType, PropField
from .serializers import (
    AccountSerializer, AccountTypeSerializer, AccountWithSecretSerializer, PropFieldSerializer
)


class AccountViewSet(JMSModelViewSet):
    permission_classes = (NamespaceRBACPermission,)
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

    def list(self, request, *args, **kwargs):
        namespace_id = request.query_params.get('namespace_id')
        if not namespace_id:
            return Response({'msg': '缺少必要参数'}, status=status.HTTP_400_BAD_REQUEST)
        self.queryset = self.filter_queryset(self.get_queryset()).filter(namespace_id=namespace_id).distinct()
        return super(AccountViewSet, self).list(request, *args, **kwargs)

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
    permission_classes = (IsSuperUser,)
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
