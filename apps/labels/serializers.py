from django.db.models import Count
from rest_framework import serializers

from .models import Label, LabeledResource

__all__ = ['LabelSerializer', 'LabeledResourceSerializer']


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
    class Meta:
        model = LabeledResource
        fields = ('id', 'label', 'res_type', 'res_id', 'date_created', 'date_updated')
        read_only_fields = ('date_created', 'date_updated')
