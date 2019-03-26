# -*- coding: utf-8 -*-
#
from rest_framework import viewsets

from common.permissions import WithBootstrapToken
from .. import serializers_v2 as serializers


class ServiceAccountRegistrationViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ServiceAccountSerializer
    permission_classes = (WithBootstrapToken,)
    http_method_names = ['post']
