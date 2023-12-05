from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .models import Label, LabeledResource

__all__ = ['LabelSerializer', 'LabeledResourceSerializer', 'ContentTypeResourceSerializer']


class LabelSerializer(BulkOrgResourceModelSerializer):
    class Meta:
        model = Label
        fields = ['id', 'name', 'value', 'res_count', 'date_created', 'date_updated']
        read_only_fields = ('date_created', 'date_updated', 'res_count')
        extra_kwargs = {
            'res_count': {'label': _('Resource count')},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.annotate(res_count=Count('labeled_resources'))
        return queryset


class LabeledResourceSerializer(serializers.ModelSerializer):
    res_type = ObjectRelatedField(
        queryset=ContentType.objects, attrs=('app_label', 'model', 'name'), label=_("Resource type")
    )
    label = ObjectRelatedField(queryset=Label.objects, attrs=('name', 'value'))
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


class ContentTypeResourceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.SerializerMethodField()

    @staticmethod
    def get_name(obj):
        return str(obj)
