from rest_framework.viewsets import GenericViewSet
from rest_framework import mixins
from rest_framework.authentication import SessionAuthentication

from common.permissions import RBACPermission
from accounts.models import Account, AccountType
from accounts.serializers import AccountSerializer, AccountTypeSerializer


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


class AccountViewSet(mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin,
                     mixins.ListModelMixin,
                     GenericViewSet):

    permission_classes = (RBACPermission,)
    # permission_classes = (IsAuthenticated,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    filter_fields = ('name', 'username', 'address', 'namespace__name')
    search_fields = filter_fields
    ordering_fields = ('username', 'address', 'namespace__name', 'date_created')

    model = Account
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

    def list(self, request, *args, **kwargs):
        # TODO return all data belong to the user's namespace when namespace_id is Null
        namespace_id = request.query_params.get('namespace_id')
        self.queryset = self.filter_queryset(self.queryset).filter(namespace_id=namespace_id)
        return super(AccountViewSet, self).list(request, *args, **kwargs)


class AccountTypeViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.DestroyModelMixin,
                         mixins.ListModelMixin,
                         GenericViewSet):

    permission_classes = (RBACPermission,)
    authentication_classes = (CsrfExemptSessionAuthentication,)

    filter_fields = ('name', 'category')
    search_fields = filter_fields
    ordering_fields = ('name', 'category', 'date_created')

    queryset = AccountType.objects.all()
    serializer_class = AccountTypeSerializer
