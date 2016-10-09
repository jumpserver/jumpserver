# ~*~ coding: utf-8 ~*~
# 


from rest_framework import generics

import serializers

from .models import ProxyLog


class ProxyLogListCreateApi(generics.ListCreateAPIView):
    queryset = ProxyLog.objects.all()
    serializer_class = serializers.ProxyLogSerializer


class ProxyLogDetailApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProxyLog.objects.all()
    serializer_class = serializers.ProxyLogSerializer


class CommandLogCreateApi(generics.CreateAPIView):
    serializer_class = serializers.CommandLogSerializer
