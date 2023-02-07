from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _

from accounts import serializers
from accounts.const import Source
from accounts.models import GatheredAccount
from accounts.filters import GatheredAccountFilterSet
from orgs.mixins.api import OrgBulkModelViewSet

__all__ = [
    'GatheredAccountViewSet',
]


class GatheredAccountViewSet(OrgBulkModelViewSet):
    model = GatheredAccount
    search_fields = ('username',)
    filterset_class = GatheredAccountFilterSet
    serializer_classes = {
        'default': serializers.GatheredAccountSerializer,
    }
    rbac_perms = {
        'sync_account': 'assets.add_gatheredaccount',
    }

    @action(methods=['post'], detail=True, url_path='sync')
    def sync_account(self, request, *args, **kwargs):
        gathered_account = super().get_object()
        asset = gathered_account.asset
        username = gathered_account.username
        accounts = asset.accounts.filter(username=username)
        if accounts.exists():
            accounts.update(source=Source.COLLECTED)
        else:
            asset.accounts.model.objects.create(
                asset=asset, username=username,
                name=f'{username}-{_("Collected")}',
                source=Source.COLLECTED
            )
        return Response(status=status.HTTP_201_CREATED)
