from django.shortcuts import get_object_or_404

from accounts.models import VirtualAccount
from accounts.serializers import VirtualAccountSerializer
from common.utils import is_uuid
from orgs.mixins.api import OrgBulkModelViewSet


class VirtualAccountViewSet(OrgBulkModelViewSet):
    serializer_class = VirtualAccountSerializer
    search_fields = ('username',)
    filterset_fields = ('username',)

    def get_queryset(self):
        return VirtualAccount.objects.all()

    def get_object(self, ):
        pk = self.kwargs.get('pk')
        kwargs = {}
        if is_uuid(pk):
            kwargs['id'] = pk
        else:
            kwargs['username'] = pk
        return get_object_or_404(VirtualAccount, **kwargs)

