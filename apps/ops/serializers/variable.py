# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField, LabeledChoiceField
from common.serializers.mixin import CommonBulkModelSerializer
from ops.const import FieldType
from ops.models import Variable, AdHoc, Job

__all__ = [
    'VariableSerializer', 'AdhocVariableSerializer', 'JobVariableSerializer'
]


class VariableSerializer(CommonBulkModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    type = LabeledChoiceField(
        choices=FieldType.choices, default=FieldType.text, label=_("参数类型")
    )

    class Meta:
        model = Variable
        read_only_fields = ["id", "date_created", "date_updated", "created_by", "creator"]
        fields = read_only_fields + [
            "name", "var_name", "type", 'required', 'default_value', 'tips', 'adhoc', 'playbook', 'job'
        ]

    @classmethod
    def setup_eager_loading(cls, queryset):
        queryset = queryset.prefetch_related('adhoc', 'job')
        return queryset


class AdhocVariableSerializer(VariableSerializer):
    adhoc = serializers.PrimaryKeyRelatedField(queryset=AdHoc.objects, required=False)

    class Meta(VariableSerializer.Meta):
        fields = VariableSerializer.Meta.fields


class JobVariableSerializer(VariableSerializer):
    job = serializers.PrimaryKeyRelatedField(queryset=Job.objects, required=False)

    class Meta(VariableSerializer.Meta):
        fields = VariableSerializer.Meta.fields
