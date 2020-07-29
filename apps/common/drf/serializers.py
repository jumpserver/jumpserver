from rest_framework.serializers import Serializer
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from rest_framework_bulk.serializers import BulkListSerializer

from common.mixins.serializers import BulkSerializerMixin
from common.mixins import BulkListSerializerMixin

__all__ = ['EmptySerializer', 'BulkModelSerializer']


class EmptySerializer(Serializer):
    pass


class BulkModelSerializer(BulkSerializerMixin, ModelSerializer):
    pass


class AdaptedBulkListSerializer(BulkListSerializerMixin, BulkListSerializer):
    pass


class CeleryTaskSerializer(serializers.Serializer):
    task = serializers.CharField(read_only=True)
