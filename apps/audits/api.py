# -*- coding: utf-8 -*-
#

from rest_framework import viewsets

from common.permissions import IsOrgAdminOrAppUser
from .models import FTPLog
from .serializers import FTPLogSerializer


class FTPLogViewSet(viewsets.ModelViewSet):
    queryset = FTPLog.objects.all()
    serializer_class = FTPLogSerializer
    permission_classes = (IsOrgAdminOrAppUser,)
