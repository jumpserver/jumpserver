# -*- coding: utf-8 -*-
#
from rest_framework import viewsets

from common.permissions import WithBootstrapToken
from ...serializers import v2 as serializers


class ServiceAccountRegistrationViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ServiceAccountRegistrationSerializer
    permission_classes = (WithBootstrapToken,)
    http_method_names = ['post']
