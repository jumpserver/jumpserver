# ~*~ coding: utf-8 ~*~
from rest_framework import serializers
from .models import (
    AssetGroup,Asset,IDC,AssetExtend
)
from rest_framework import viewsets,serializers

class AssetGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetGroup
        #exclude = [
            #'password', 'first_name', 'last_name', 'secret_key_otp',
            #'private_key', 'public_key', 'avatar',
        #]

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        #fields = ('id', 'title', 'code', 'linenos', 'language', 'style')

class IDCSerializer(serializers.ModelSerializer):
    class Meta:
        model = IDC
        #fields = ('id', 'title', 'code', 'linenos', 'language', 'style')


class AssetGroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows AssetGroup to be viewed or edited.
    """
    queryset = AssetGroup.objects.all()
    serializer_class = AssetGroupSerializer


class AssetViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer


class IDCViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows IDC to be viewed or edited.
    """
    queryset = IDC.objects.all()
    serializer_class = IDCSerializer