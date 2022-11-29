# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

import datetime

from rest_framework import serializers

from common.drf.fields import ReadableHiddenField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import AdHoc


class AdHocSerializer(BulkOrgResourceModelSerializer, serializers.ModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    row_count = serializers.IntegerField(read_only=True)
    size = serializers.IntegerField(read_only=True)

    class Meta:
        model = AdHoc
        fields = ["id", "name", "module", "row_count", "size", "args", "creator", "comment", "date_created",
                  "date_updated"]
