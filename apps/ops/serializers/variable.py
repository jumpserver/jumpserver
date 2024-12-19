# -*- coding: utf-8 -*-
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from common.serializers.fields import ReadableHiddenField, LabeledChoiceField, EncryptedField
from common.serializers.mixin import CommonBulkModelSerializer
from ops.const import FieldType
from ops.models import Variable, AdHoc, Job, Playbook

__all__ = [
    'VariableSerializer', 'AdhocVariableSerializer', 'JobVariableSerializer', 'PlaybookVariableSerializer',
    'VariableFormDataSerializer'
]


class VariableSerializer(CommonBulkModelSerializer):
    name = serializers.CharField(max_length=1024, label=_('Name'), required=True)
    var_name = serializers.CharField(
        max_length=1024, required=True, label=_('Variable name'),
        help_text=_("The variable name used in the script has a fixed prefix 'jms_' followed by the input variable "
                    "name. For example, if the variable name is 'name,' the final generated environment variable will "
                    "be 'jms_name'.")
    )
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    type = LabeledChoiceField(
        choices=FieldType.choices, default=FieldType.text, label=_("Variable Type")
    )
    default_value = serializers.CharField(max_length=2048, label=_('Default Value'), required=False, allow_blank=True)
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
            data['select_default_value'] = instance.default_value
        if instance.type == FieldType.text:
            data['text_default_value'] = instance.default_value
        data['extra_args'] = instance.extra_args.get('options', '')
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

        if not any([job, adhoc, playbook]):
            raise ValidationError("One of 'job', 'adhoc', or 'playbook' is required.")

        try:
            variables = Variable.objects.filter(
                job=job if job else None,
                adhoc=adhoc if adhoc else None,
                playbook=playbook if playbook else None
            ).all()
        except ObjectDoesNotExist:
            raise ValidationError("Invalid job, adhoc, or playbook ID.")

        dynamic_fields = [var.form_data for var in variables]

        for field in dynamic_fields:
            self._add_field(field)

    def _add_field(self, field):
        field_type = field['type']
        required = field['required']
        var_name = field["var_name"]
        label = field["label"]
        help_text = field['help_text']
        default = field.get('default', None)

        if field_type == FieldType.text:
            self.fields[var_name] = serializers.CharField(
                max_length=1024, label=label, help_text=help_text, required=required
            )
        elif field_type == FieldType.select:
            self._add_select_field(field, var_name, required, label, help_text)

        if required and default is not None:
            self.fields[var_name].default = default

    def _add_select_field(self, field, var_name, required, label, help_text):
        extra_args = field.get('extra_args', {})
        options = extra_args.get('options', '').splitlines()

        try:
            options_data = {option.split(':')[0]: option.split(':')[1] for option in options}
        except Exception as e:
            raise ValidationError(f"Invalid options format: {str(e)}")

        DynamicFieldType = models.TextChoices('DynamicFieldType', options_data)
        self.fields[var_name] = LabeledChoiceField(
            choices=DynamicFieldType.choices, required=required, label=label,
            help_text=help_text
        )
