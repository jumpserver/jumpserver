# ~*~ coding: utf-8 ~*~
# 


from rest_framework import generics

import serializers


class ProxyLogCreateApi(generics.CreateAPIView):
    serializer_class = serializers.ProxyLogSerializer


class CommandLogCreateApi(generics.CreateAPIView):
    serializer_class = serializers.CommandLogSerializer
