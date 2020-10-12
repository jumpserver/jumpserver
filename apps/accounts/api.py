from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import DjangoModelPermissions

from common.permissions import RBACPermission
from common.drf.api import JMSModelViewSet
from .models import Account, AccountType
from .serializers import AccountSerializer, AccountTypeSerializer, AccountWithSecretSerializer


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

    def list(self, request, *args, **kwargs):
        namespace_id = request.query_params.get('namespace_id')
        if not namespace_id:
            return Response({"msg": _("namespace's id is required")}, status=400)
        self.queryset = self.filter_queryset(self.get_queryset())\
            .filter(namespace_id=namespace_id)
        return super().list(request, *args, **kwargs)

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
