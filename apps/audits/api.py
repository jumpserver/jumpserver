# -*- coding: utf-8 -*-
#

from rest_framework import viewsets

from common.permissions import IsSuperUserOrAppUser
from .models import FTPLog
from .serializers import FTPLogSerializer


class FTPLogViewSet(viewsets.ModelViewSet):
    queryset = FTPLog.objects
    serializer_class = FTPLogSerializer
    permission_classes = (IsSuperUserOrAppUser,)
