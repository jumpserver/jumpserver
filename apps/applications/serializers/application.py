# coding: utf-8
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.models import Organization
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.serializers import MethodSerializer
from .attrs import category_serializer_classes_mapping, type_serializer_classes_mapping
from .. import models
from .. import const

__all__ = [
    'ApplicationSerializer', 'ApplicationSerializerMixin', 'MiniApplicationSerializer',
    'ApplicationAccountSerializer', 'ApplicationAccountSecretSerializer'
]


class ApplicationSerializerMixin(serializers.Serializer):
    attrs = MethodSerializer()

    def get_attrs_serializer(self):
        default_serializer = serializers.Serializer(read_only=True)
        if isinstance(self.instance, models.Application):
            _type = self.instance.type
            _category = self.instance.category
        else:
            _type = self.context['request'].query_params.get('type')
            _category = self.context['request'].query_params.get('category')

        if _type:
            serializer_class = type_serializer_classes_mapping.get(_type)
        elif _category:
            serializer_class = category_serializer_classes_mapping.get(_category)
        else:
            serializer_class = default_serializer

        if not serializer_class:
            serializer_class = default_serializer

        if isinstance(serializer_class, type):
            serializer = serializer_class()
        else:
            serializer = serializer_class
        return serializer


class ApplicationSerializer(ApplicationSerializerMixin, BulkOrgResourceModelSerializer):
    category_display = serializers.ReadOnlyField(source='get_category_display', label=_('Category display'))
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type display'))

    class Meta:
        model = models.Application
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'category', 'category_display', 'type', 'type_display',
            'attrs', 'date_created', 'date_updated', 'created_by', 'comment'
        ]
        fields_fk = ['domain']
        fields = fields_small + fields_fk
        read_only_fields = [
            'created_by', 'date_created', 'date_updated', 'get_type_display',
        ]

    def validate_attrs(self, attrs):
        _attrs = self.instance.attrs if self.instance else {}
        _attrs.update(attrs)
        return _attrs


class ApplicationAccountSerializer(serializers.Serializer):
    id = serializers.ReadOnlyField(label=_("Id"), source='uid')
    username = serializers.ReadOnlyField(label=_("Username"))
    password = serializers.CharField(write_only=True, label=_("Password"))
    systemuser = serializers.ReadOnlyField(label=_('System user'))
    systemuser_display = serializers.ReadOnlyField(label=_("System user display"))
    app = serializers.ReadOnlyField(label=_('App'))
    app_name = serializers.ReadOnlyField(label=_("Application name"), read_only=True)
    category = serializers.ChoiceField(label=_('Category'), choices=const.AppCategory.choices, read_only=True)
    category_display = serializers.SerializerMethodField(label=_('Category display'))
    type = serializers.ChoiceField(label=_('Type'), choices=const.AppType.choices, read_only=True)
    type_display = serializers.SerializerMethodField(label=_('Type display'))
    uid = serializers.ReadOnlyField(label=_("Union id"))
    org_id = serializers.ReadOnlyField(label=_("Organization"))
    org_name = serializers.SerializerMethodField(label=_("Org name"))

    category_mapper = dict(const.AppCategory.choices)
    type_mapper = dict(const.AppType.choices)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    def get_category_display(self, obj):
        return self.category_mapper.get(obj['category'])

    def get_type_display(self, obj):
        return self.type_mapper.get(obj['type'])

    @staticmethod
    def get_org_name(obj):
        org = Organization.get_instance(obj['org_id'])
        return org.name


class ApplicationAccountSecretSerializer(ApplicationAccountSerializer):
    password = serializers.CharField(write_only=False, label=_("Password"))


class MiniApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Application
        fields = ApplicationSerializer.Meta.fields_mini
