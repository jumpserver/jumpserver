# -*- coding: utf-8 -*-
#

from orgs.mixins.api import OrgModelViewSet
from assets.models import GatheredUser
from common.permissions import IsOrgAdmin

from ..serializers import GatheredUserSerializer
from ..filters import AssetRelatedByNodeFilterBackend


__all__ = ['GatheredUserViewSet']


class GatheredUserViewSet(OrgModelViewSet):
    model = GatheredUser
    serializer_class = GatheredUserSerializer
    permission_classes = [IsOrgAdmin]
    extra_filter_backends = [AssetRelatedByNodeFilterBackend]

    filter_fields = ['asset', 'username', 'present']
    search_fields = ['username', 'asset__ip', 'asset__hostname']
