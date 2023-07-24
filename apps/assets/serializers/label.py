# -*- coding: utf-8 -*-
#
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import Label


class LabelSerializer(BulkOrgResourceModelSerializer):
    asset_count = serializers.ReadOnlyField(label=_("Assets amount"))

    class Meta:
        model = Label
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'value', 'category', 'is_active',
            'date_created', 'comment',
        ]
        fields_m2m = ['asset_count', 'assets']
        fields = fields_small + fields_m2m
        read_only_fields = (
            'category', 'date_created', 'asset_count',
        )
        extra_kwargs = {
            'assets': {'required': False, 'label': _('Asset')}
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        queryset = queryset.prefetch_related('assets') \
            .annotate(asset_count=Count('assets'))
        return queryset


class LabelDistinctSerializer(BulkOrgResourceModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = Label
        fields = ("name", "value")

    @staticmethod
    def get_value(obj):
        labels = Label.objects.filter(name=obj["name"])
        return ', '.join([label.value for label in labels])
