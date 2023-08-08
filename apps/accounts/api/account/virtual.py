from django.shortcuts import get_object_or_404

from accounts.models import VirtualAccount
from accounts.serializers import VirtualAccountSerializer
from common.utils import is_uuid
from orgs.mixins.api import OrgBulkModelViewSet


class VirtualAccountViewSet(OrgBulkModelViewSet):
    serializer_class = VirtualAccountSerializer
    search_fields = ('alias',)
    filterset_fields = ('alias',)

    def get_queryset(self):
        return VirtualAccount.get_or_init_queryset()

    def get_object(self, ):
        pk = self.kwargs.get('pk')
        kwargs = {'pk': pk} if is_uuid(pk) else {'alias': pk}
        return get_object_or_404(VirtualAccount, **kwargs)
