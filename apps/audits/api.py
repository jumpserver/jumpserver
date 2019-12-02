# -*- coding: utf-8 -*-
#

from common.permissions import IsOrgAdminOrAppUser, IsOrgAuditor
from orgs.mixins.api import OrgModelViewSet
from .models import FTPLog
from .serializers import FTPLogSerializer


class FTPLogViewSet(OrgModelViewSet):
    model = FTPLog
    serializer_class = FTPLogSerializer
    permission_classes = (IsOrgAdminOrAppUser | IsOrgAuditor,)
    http_method_names = ['get', 'post', 'head', 'options']
