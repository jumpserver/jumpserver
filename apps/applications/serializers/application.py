# coding: utf-8
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.serializers import MethodSerializer
from .attrs import category_serializer_classes_mapping, type_serializer_classes_mapping
from assets.serializers import SystemUserSerializer
from .. import models
from .. import const

__all__ = [
    'ApplicationSerializer', 'ApplicationSerializerMixin',
    'ApplicationAccountSerializer', 'ApplicationAccountWithAuthInfoSerializer'
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
    category_display = serializers.ReadOnlyField(source='get_category_display', label=_('Category(Display)'))
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type(Dispaly)'))

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
    username = serializers.CharField(label=_("Username"))
    password = serializers.CharField(write_only=True, label=_("Password"))
    app_name = serializers.ReadOnlyField(label=_("Application name"))
    app_category = serializers.ChoiceField(label=_('Category'), choices=const.ApplicationCategoryChoices.choices)
    app_category_display = serializers.SerializerMethodField(label=_('Category'))
    app_type = serializers.ChoiceField(label=_('Type'), choices=const.ApplicationTypeChoices.choices)
    app_type_display = serializers.SerializerMethodField(label=_('Type'))

    category_mapper = dict(const.ApplicationCategoryChoices.choices)
    type_mapper = dict(const.ApplicationTypeChoices.choices)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    def get_app_category_display(self, obj):
        return self.category_mapper.get(obj.category)

    def get_app_type_display(self, obj):
        return self.type_mapper.get(obj.type)


class ApplicationAccountWithAuthInfoSerializer(ApplicationAccountSerializer):
    password = serializers.CharField(write_only=False, label=_("Password"))
    # class Meta(ApplicationAccountSerializer.Meta):
    #     fields = ApplicationAccountSerializer.Meta.fields + ['password', 'token']
