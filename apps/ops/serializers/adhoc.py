# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers import WritableNestedModelSerializer
from common.serializers.fields import ReadableHiddenField, ObjectRelatedField
from common.serializers.mixin import CommonBulkModelSerializer
from .mixin import ScopeSerializerMixin
from ..models import AdHoc
from ops.serializers import AdhocVariableSerializer


class AdHocSerializer(ScopeSerializerMixin, CommonBulkModelSerializer, WritableNestedModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    variable = AdhocVariableSerializer(many=True, required=False, allow_null=True, label=_('Variable'))

    class Meta:
        model = AdHoc
        read_only_field = ["id", "creator", "date_created", "date_updated", "created_by"]
        fields_m2m = ['variable']
        fields = read_only_field + fields_m2m + ["id", "name", "scope", "module", "args", "comment"]
