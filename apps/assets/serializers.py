# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from rest_framework import viewsets, serializers,generics
from .models import AssetGroup, Asset, IDC, AssetExtend
from common.mixins import BulkDeleteApiMixin
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin

class AssetBulkUpdateSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    # group_display = serializers.SerializerMethodField()
    # active_display = serializers.SerializerMethodField()
    #groups = serializers.PrimaryKeyRelatedField(many=True, queryset=AssetGroup.objects.all())

    class Meta(object):
        model = Asset
        list_serializer_class = BulkListSerializer
        fields = ['id', 'port', 'idc']

    # def get_group_display(self, obj):
    #     return " ".join([group.name for group in obj.groups.all()])
    #
    # def get_active_display(self, obj):
    #     # TODO: user ative state
    #     return not (obj.is_expired and obj.is_active)