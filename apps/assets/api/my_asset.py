# -*- coding: utf-8 -*-
#
from common.api import GenericViewSet
from rest_framework.mixins import CreateModelMixin
from common.permissions import IsValidUser
from ..serializers import MyAssetSerializer

__all__ = ['MyAssetViewSet']


class MyAssetViewSet(CreateModelMixin, GenericViewSet):
    serializer_class = MyAssetSerializer
    permission_classes = (IsValidUser,)
