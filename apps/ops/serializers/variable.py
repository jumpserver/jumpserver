# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField, LabeledChoiceField, EncryptedField
from common.serializers.mixin import CommonBulkModelSerializer
from ops.const import FieldType
from ops.models import Variable, AdHoc, Job, Playbook

__all__ = [
    'VariableSerializer', 'AdhocVariableSerializer', 'JobVariableSerializer', 'PlaybookVariableSerializer',
    'VariableFormDataSerializer'
]


class VariableSerializer(CommonBulkModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    type = LabeledChoiceField(
        choices=FieldType.choices, default=FieldType.text, label=_("Variable Type")
    )
    extra_args = serializers.CharField(
        max_length=1024, label=_("ExtraVars"), required=False, allow_blank=True,
        help_text=_(
            "Each item is on a separate line, with each line separated by a colon. The part before the colon is the "
            "display content, and the part after the colon is the value.")
    )

    class Meta:
        model = Variable
        read_only_fields = ["id", "date_created", "date_updated", "created_by", "creator"]
        fields = read_only_fields + [
            "name", "var_name", "type", 'required', 'default_value', 'tips', 'adhoc', 'playbook', 'job', 'form_data',
            'extra_args'
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        type = attrs.get('type')
        attrs['extra_args'] = {}
        if type == FieldType.text:
            attrs['default_value'] = self.initial_data.get('text_default_value')
        elif type == FieldType.select:
            attrs['default_value'] = self.initial_data.get('select_default_value')
            options = self.initial_data.get('extra_args', '')
            attrs['extra_args'] = {"options": options}
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.type == FieldType.select:
            data['extra_args'] = instance.extra_args.get('options', '')
            data['select_default_value'] = instance.default_value
        if instance.type == FieldType.text:
            data['text_default_value'] = instance.default_value
        return data

    @classmethod
    def setup_eager_loading(cls, queryset):
        queryset = queryset.prefetch_related('adhoc', 'job', 'playbook')
        return queryset


class AdhocVariableSerializer(VariableSerializer):
    adhoc = serializers.PrimaryKeyRelatedField(queryset=AdHoc.objects, required=False)

    class Meta(VariableSerializer.Meta):
        fields = VariableSerializer.Meta.fields


class JobVariableSerializer(VariableSerializer):
    job = serializers.PrimaryKeyRelatedField(queryset=Job.objects, required=False)

    class Meta(VariableSerializer.Meta):
        fields = VariableSerializer.Meta.fields


class PlaybookVariableSerializer(VariableSerializer):
    playbook = serializers.PrimaryKeyRelatedField(queryset=Playbook.objects, required=False)

    class Meta(VariableSerializer.Meta):
        fields = VariableSerializer.Meta.fields


def create_dynamic_text_choices(options):
    """
    动态创建一个 TextChoices 子类。`options` 应该是一个列表，
    格式为 [(value1, display1), (value2, display2), ...]
    """
    attrs = {
        key.upper(): value for value, key in options
    }
    attrs['choices'] = options
    return type('DynamicTextChoices', (models.TextChoices,), attrs)


class VariableFormDataSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request:
            return
        params = request.query_params
        if params.get('format') == 'openapi':
            return
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
                if field_type == FieldType.text:
                    self.fields[var_name] = serializers.CharField(
                        max_length=1024, label=label, help_text=help_text, required=required
                    )
                elif field_type == FieldType.select:
                    extra_args = field.get('extra_args', {})
                    options = extra_args.get('options', '').splitlines()

                    DynamicFieldType = models.TextChoices(
                        'DynamicFieldType',
                        {
                            option.split(':')[0]: option.split(':')[1] for option in
                            options
                        }
                    )
                    self.fields[var_name] = LabeledChoiceField(
                        choices=DynamicFieldType.choices, required=required, label=label,
                        help_text=help_text
                    )
                if required and default is not None:
                    self.fields[var_name].default = default
