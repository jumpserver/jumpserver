# coding: utf-8
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from assets.serializers.base import AuthSerializerMixin
from common.drf.serializers import MethodSerializer, SecretReadableMixin
from .attrs import (
    category_serializer_classes_mapping,
    type_serializer_classes_mapping,
    type_secret_serializer_classes_mapping
)
from .. import models
from .. import const

__all__ = [
    'AppSerializer', 'MiniAppSerializer', 'AppSerializerMixin',
    'AppAccountSerializer', 'AppAccountSecretSerializer', 'AppAccountBackUpSerializer'
]


class AppSerializerMixin(serializers.Serializer):
    attrs = MethodSerializer()

    @property
    def app(self):
        if isinstance(self.instance, models.Application):
            instance = self.instance
        else:
            instance = None
        return instance

    def get_attrs_serializer(self):
        instance = self.app
        tp = getattr(self, 'tp', None)
        default_serializer = serializers.Serializer(read_only=True)
        if not tp:
            if instance:
                tp = instance.type
                category = instance.category
            else:
                tp = self.context['request'].query_params.get('type')
                category = self.context['request'].query_params.get('category')
        if tp:
            if isinstance(self, AppAccountBackUpSerializer):
                serializer_class = type_secret_serializer_classes_mapping.get(tp)
            else:
                serializer_class = type_serializer_classes_mapping.get(tp)
        elif category:
            serializer_class = category_serializer_classes_mapping.get(category)
        else:
            serializer_class = default_serializer

        if not serializer_class:
            serializer_class = default_serializer

        if isinstance(serializer_class, type):
            serializer = serializer_class()
        else:
            serializer = serializer_class
        return serializer

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class AppSerializer(AppSerializerMixin, BulkOrgResourceModelSerializer):
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


class MiniAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Application
        fields = AppSerializer.Meta.fields_mini


class AppAccountSerializer(AppSerializerMixin, AuthSerializerMixin, BulkOrgResourceModelSerializer):
    category = serializers.ChoiceField(label=_('Category'), choices=const.AppCategory.choices, read_only=True)
    category_display = serializers.SerializerMethodField(label=_('Category display'))
    type = serializers.ChoiceField(label=_('Type'), choices=const.AppType.choices, read_only=True)
    type_display = serializers.SerializerMethodField(label=_('Type display'))
    date_created = serializers.DateTimeField(label=_('Date created'), format="%Y/%m/%d %H:%M:%S", read_only=True)
    date_updated = serializers.DateTimeField(label=_('Date updated'), format="%Y/%m/%d %H:%M:%S", read_only=True)

    category_mapper = dict(const.AppCategory.choices)
    type_mapper = dict(const.AppType.choices)

    class Meta:
        model = models.Account
        fields_mini = ['id', 'username', 'version']
        fields_write_only = ['password', 'private_key', 'public_key', 'passphrase']
        fields_other = ['date_created', 'date_updated']
        fields_fk = ['systemuser', 'systemuser_display', 'app', 'app_display']
        fields = fields_mini + fields_fk + fields_write_only + fields_other + [
            'type', 'type_display', 'category', 'category_display', 'attrs'
        ]
        extra_kwargs = {
            'username': {'default': '', 'required': False},
            'password': {'write_only': True},
            'app_display': {'label': _('Application display')},
            'systemuser_display': {'label': _('System User')},
            'account': {'label': _('account')}
        }
        use_model_bulk_create = True
        model_bulk_create_kwargs = {
            'ignore_conflicts': True
        }

    @property
    def app(self):
        if isinstance(self.instance, models.Account):
            instance = self.instance.app
        else:
            instance = None
        return instance

    def get_category_display(self, obj):
        return self.category_mapper.get(obj.category)

    def get_type_display(self, obj):
        return self.type_mapper.get(obj.type)

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('systemuser', 'app')
        return queryset

    def to_representation(self, instance):
        instance.load_auth()
        return super().to_representation(instance)


class AppAccountSecretSerializer(SecretReadableMixin, AppAccountSerializer):
    class Meta(AppAccountSerializer.Meta):
        extra_kwargs = {
            'password': {'write_only': False},
            'private_key': {'write_only': False},
            'public_key': {'write_only': False},
            'app_display': {'label': _('Application display')},
            'systemuser_display': {'label': _('System User')}
        }


class AppAccountBackUpSerializer(AppAccountSecretSerializer):
    class Meta(AppAccountSecretSerializer.Meta):
        fields = [
            'id', 'app_display', 'attrs', 'username', 'password', 'private_key',
            'public_key', 'date_created', 'date_updated', 'version'
        ]

    def __init__(self, *args, **kwargs):
        self.tp = kwargs.pop('tp', None)
        super().__init__(*args, **kwargs)

    @classmethod
    def setup_eager_loading(cls, queryset):
        return queryset

    def to_representation(self, instance):
        return super(AppAccountSerializer, self).to_representation(instance)
