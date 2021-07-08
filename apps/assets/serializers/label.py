# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from ..models import Label


class LabelSerializer(BulkOrgResourceModelSerializer):
    asset_count = serializers.SerializerMethodField(label=_("Assets amount"))
    category_display = serializers.ReadOnlyField(source='get_category_display', label=_('Category display'))

    class Meta:
        model = Label
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'value', 'category', 'category_display',
            'is_active',
            'date_created',
            'comment',
        ]
        fields_m2m = ['asset_count', 'assets']
        fields = fields_small + fields_m2m
        read_only_fields = (
            'category', 'date_created', 'asset_count',
        )
        extra_kwargs = {
            'assets': {'required': False}
        }

    @staticmethod
    def get_asset_count(obj):
        return obj.assets.count()

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(['get_category_display'])
        return fields


class LabelDistinctSerializer(BulkOrgResourceModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = Label
        fields = ("name", "value")

    @staticmethod
    def get_value(obj):
        labels = Label.objects.filter(name=obj["name"])
        return ', '.join([label.value for label in labels])
