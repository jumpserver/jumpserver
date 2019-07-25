# -*- coding: utf-8 -*-
#

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView

from .. import serializers


class TokenCreateApi(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.BearerTokenSerializer

