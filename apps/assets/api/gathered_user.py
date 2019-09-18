# -*- coding: utf-8 -*-
#

from orgs.mixins.api import OrgModelViewSet
from assets.models import GatheredUser
from common.permissions import IsOrgAdmin

from ..serializers import GatheredUserSerializer


__all__ = ['GatheredUserViewSet']


class GatheredUserViewSet(OrgModelViewSet):
    queryset = GatheredUser.objects.all()
    serializer_class = GatheredUserSerializer
    permission_classes = [IsOrgAdmin]

    filter_fields = ['asset', 'username', 'present']
    search_fields = ['username', 'asset__ip', 'asset__hostname']


