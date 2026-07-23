from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from common.validators import ProjectUniqueValidator
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .const import label_resource_types
from .models import Label, LabeledResource

__all__ = ['LabelSerializer', 'LabeledResourceSerializer', 'ContentTypeResourceSerializer']


class LabelSerializer(BulkOrgResourceModelSerializer):
    class Meta:
        model = Label
        relation_count_fields = {
            'res_count': 'labeled_resources',
        }
        amount_fields = list(relation_count_fields)
        fields = ['id', 'name', 'value', 'color'] + amount_fields + [
            'comment', 'date_created', 'date_updated'
        ]
        read_only_fields = ('date_created', 'date_updated', 'res_count')
        extra_kwargs = {
            'res_count': {'label': _('Resource count')},
        }

    @staticmethod
    def validate_name(value):
        if ':' in value or ',' in value:
            raise serializers.ValidationError(_('Cannot contain ":,"'))
        return value

    def validate_value(self, value):
        return self.validate_name(value)

    @classmethod
    def validate_name_value(cls, name, value):
        serializer = cls(data={'name': name, 'value': value})
        serializer.validators = [
            v for v in serializer.validators
            if not isinstance(v, (serializers.UniqueTogetherValidator, ProjectUniqueValidator))
        ]
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

class LabeledResourceSerializer(serializers.ModelSerializer):
    res_type = LabeledChoiceField(
        choices=[], label=_("Resource type"), source='res_type_id', required=False
    )
    label = ObjectRelatedField(queryset=Label.objects, attrs=('id', 'display_name'), label=_("Label"))
    resource = serializers.CharField(label=_("Resource"))

    class Meta:
        model = LabeledResource
        fields = ('id', 'label', 'res_type', 'res_id', 'date_created', 'resource', 'date_updated')
        read_only_fields = ('date_created', 'date_updated', 'resource')

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.select_related('label', 'res_type')
        return queryset

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_res_type_choices()

    def set_res_type_choices(self):
        res_type_field = self.fields.get('res_type')
        if not res_type_field:
            return

        res_type_field.choices = [(ct.id, ct.name) for ct in label_resource_types]


class ContentTypeResourceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.SerializerMethodField()

    @staticmethod
    def get_name(obj) -> str:
        return str(obj)
