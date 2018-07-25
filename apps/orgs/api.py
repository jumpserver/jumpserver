# -*- coding: utf-8 -*-
#

from rest_framework import viewsets

from common.permissions import IsOrgAdminOrAppUser
from .models import Organization
from .serializers import OrgSerializer


class OrgViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrgSerializer
    permission_classes = (IsOrgAdminOrAppUser,)
