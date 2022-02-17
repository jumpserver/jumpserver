# coding: utf-8
#

from orgs.mixins import generics
from .. import models
from ..serializers import RemoteAppConnectionInfoSerializer


__all__ = [
    'RemoteAppConnectionInfoApi',
]


class RemoteAppConnectionInfoApi(generics.RetrieveAPIView):
    model = models.Application
    serializer_class = RemoteAppConnectionInfoSerializer
