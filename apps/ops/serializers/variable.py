# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField, LabeledChoiceField
from common.serializers.mixin import CommonBulkModelSerializer
from ops.const import FieldType
from ops.models import Variable, AdHoc, Job

__all__ = [
    'VariableSerializer', 'AdhocVariableSerializer', 'JobVariableSerializer', 'VariableFormDataSerializer'
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
            "name", "var_name", "type", 'required', 'default_value', 'tips', 'adhoc', 'playbook', 'job', 'form_data'
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


class VariableFormDataSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request:
            return
        params = request.query_params
        job = params.get('job')
        adhoc = params.get('adhoc')
        playbook = params.get('playbook')
        if job:
            variables = Variable.objects.filter(job=job).all()
        elif adhoc:
            variables = Variable.objects.filter(adhoc=adhoc).all()
        else:
            variables = Variable.objects.filter(playbook=playbook).all()
        dynamic_fields = [var.form_data for var in variables]

        if dynamic_fields:
            for field in dynamic_fields:
                field_type = field['type']
                required = field['required']
                var_name = field["var_name"]
                label = field["label"]
                help_text = field['help_text']
                default = field['default']

                self.fields[var_name] = serializers.CharField(
                    max_length=1024, label=label, help_text=help_text, default=default
                )
                if required and default is not None:
                    self.fields[var_name].default = default
