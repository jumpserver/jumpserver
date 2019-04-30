# -*- coding: utf-8 -*-
#

from .mixins import BulkListSerializerMixin
from rest_framework_bulk.serializers import BulkListSerializer


class AdaptedBulkListSerializer(BulkListSerializerMixin, BulkListSerializer):
    pass
