# -*- coding: utf-8 -*-
#

from rest_framework_bulk.serializers import BulkListSerializer
from rest_framework import serializers
from .mixins import BulkListSerializerMixin


class AdaptedBulkListSerializer(BulkListSerializerMixin, BulkListSerializer):
    pass


class CeleryTaskSerializer(serializers.Serializer):
    task = serializers.CharField(read_only=True)
