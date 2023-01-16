# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import AdHoc


class AdHocSerializer(BulkOrgResourceModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = AdHoc
        read_only_field = ["id", "creator", "date_created", "date_updated"]
        fields = read_only_field + ["id", "name", "module", "args", "comment"]
