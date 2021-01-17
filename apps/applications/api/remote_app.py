# coding: utf-8
#

from orgs.mixins import generics
from ..hands import IsAppUser
from .. import models
from ..serializers import RemoteAppConnectionInfoSerializer
from ..permissions import IsRemoteApp


__all__ = [
    'RemoteAppConnectionInfoApi',
]


class RemoteAppConnectionInfoApi(generics.RetrieveAPIView):
    model = models.Application
    permission_classes = (IsAppUser, IsRemoteApp)
    serializer_class = RemoteAppConnectionInfoSerializer
