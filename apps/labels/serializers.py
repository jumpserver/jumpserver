from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from rest_framework import serializers

from common.serializers.fields import ObjectRelatedField
from .models import Label, LabeledResource

__all__ = ['LabelSerializer', 'LabeledResourceSerializer', 'ContentTypeResourceSerializer']


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ('id', 'name', 'value', 'res_count', 'date_created', 'date_updated')

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.annotate(res_count=Count('labeled_resources'))
        return queryset


class LabeledResourceSerializer(serializers.ModelSerializer):
    res_type = ObjectRelatedField(queryset=ContentType.objects, attrs=('app_label', 'model', 'name'))
    label = ObjectRelatedField(queryset=Label.objects, attrs=('name', 'value'))

    class Meta:
        model = LabeledResource
        fields = ('id', 'label', 'res_type', 'res_id', 'date_created', 'date_updated')
        read_only_fields = ('date_created', 'date_updated')

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.select_related('label', 'res_type')
        return queryset


class ContentTypeResourceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.SerializerMethodField()

    @staticmethod
    def get_name(obj):
        return str(obj)
