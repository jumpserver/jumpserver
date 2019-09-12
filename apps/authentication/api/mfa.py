# -*- coding: utf-8 -*-
#
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView

from .. import serializers


class MFAChallengeApi(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.MFAChallengeSerializer
