# -*- coding: utf-8 -*-
#
from rest_framework import generics

from common.mixins.api.object import GetObjectMixin
from .api import OrgQuerySetMixin


class ListAPIView(GetObjectMixin, OrgQuerySetMixin, generics.ListAPIView):
    pass


class RetrieveAPIView(GetObjectMixin, OrgQuerySetMixin, generics.RetrieveAPIView):
    pass


class CreateAPIView(GetObjectMixin, OrgQuerySetMixin, generics.CreateAPIView):
    pass


class DestroyAPIView(GetObjectMixin, OrgQuerySetMixin, generics.DestroyAPIView):
    pass


class ListCreateAPIView(GetObjectMixin, OrgQuerySetMixin, generics.ListCreateAPIView):
    pass


class UpdateAPIView(GetObjectMixin, OrgQuerySetMixin, generics.UpdateAPIView):
    pass


class RetrieveUpdateAPIView(GetObjectMixin, OrgQuerySetMixin, generics.RetrieveUpdateAPIView):
    pass


class RetrieveDestroyAPIView(GetObjectMixin, OrgQuerySetMixin, generics.RetrieveDestroyAPIView):
    pass


class RetrieveUpdateDestroyAPIView(GetObjectMixin, OrgQuerySetMixin, generics.RetrieveUpdateDestroyAPIView):
    pass
