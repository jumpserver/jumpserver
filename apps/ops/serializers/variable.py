# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField, LabeledChoiceField
from common.serializers.mixin import CommonBulkModelSerializer
from ops.const import FieldType
from ops.models import Variable


class VariableSerializer(CommonBulkModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    type = LabeledChoiceField(
        choices=FieldType.choices, default=FieldType.text, label=_("参数类型")
    )

    class Meta:
        model = Variable
        read_only_fields = ["id", "date_created", "date_updated", "created_by", "creator"]
        fields = read_only_fields + [
            "name", "username", "type", 'require', 'default_value', 'tips'
        ]
