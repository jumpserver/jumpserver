# -*- coding: utf-8 -*-
# 

from rest_framework.generics import ListCreateAPIView

from .models import Terminal
from .serializers import TerminalSerializer


class TerminalApi(ListCreateAPIView):
    queryset = Terminal.objects.all()
    serializer_class = TerminalSerializer


