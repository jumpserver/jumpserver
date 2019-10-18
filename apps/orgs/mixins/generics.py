# -*- coding: utf-8 -*-
#
from rest_framework import generics

from .api import OrgQuerySetMixin


class ListAPIView(OrgQuerySetMixin, generics.ListAPIView):
    pass


class RetrieveAPIView(OrgQuerySetMixin, generics.RetrieveAPIView):
    pass


class CreateAPIView(OrgQuerySetMixin, generics.CreateAPIView):
    pass


class DestroyAPIView(OrgQuerySetMixin, generics.DestroyAPIView):
    pass


class ListCreateAPIView(OrgQuerySetMixin, generics.ListCreateAPIView):
    pass


class UpdateAPIView(OrgQuerySetMixin, generics.UpdateAPIView):
    pass


class RetrieveUpdateAPIView(OrgQuerySetMixin, generics.RetrieveUpdateAPIView):
    pass


class RetrieveDestroyAPIView(OrgQuerySetMixin, generics.RetrieveDestroyAPIView):
    pass


class RetrieveUpdateDestroyAPIView(OrgQuerySetMixin, generics.RetrieveUpdateDestroyAPIView):
    pass
