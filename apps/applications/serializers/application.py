# coding: utf-8
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.serializers import MethodSerializer
from .attrs import category_serializer_classes_mapping, type_serializer_classes_mapping
from assets.serializers import SystemUserSerializer
from .. import models

__all__ = [
    'ApplicationSerializer', 'ApplicationSerializerMixin',
    'ApplicationUserSerializer', 'ApplicationUserWithAuthInfoSerializer'
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
            'category', 'category_display', 'type', 'type_display', 'attrs',
            'date_created', 'date_updated',
            'created_by', 'comment'
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


class ApplicationUserSerializer(SystemUserSerializer):
    application_name = serializers.SerializerMethodField(label=_('Application name'))
    application_category = serializers.SerializerMethodField(label=_('Application category'))
    application_type = serializers.SerializerMethodField(label=_('Application type'))

    class Meta(SystemUserSerializer.Meta):
        model = models.ApplicationUser
        fields_mini = [
            'id', 'application_name', 'application_category', 'application_type', 'name', 'username'
        ]
        fields_small = fields_mini + [
            'protocol', 'login_mode', 'login_mode_display', 'priority',
            "username_same_with_user", 'comment',
        ]
        fields = fields_small
        extra_kwargs = {
            'login_mode_display': {'label': _('Login mode display')},
            'created_by': {'read_only': True},
        }

    @property
    def application(self):
        return self.context['application']

    def get_application_name(self, obj):
        return self.application.name

    def get_application_category(self, obj):
        return self.application.get_category_display()

    def get_application_type(self, obj):
        return self.application.get_type_display()


class ApplicationUserWithAuthInfoSerializer(ApplicationUserSerializer):

    class Meta(ApplicationUserSerializer.Meta):
        fields = ApplicationUserSerializer.Meta.fields + ['password', 'token']
