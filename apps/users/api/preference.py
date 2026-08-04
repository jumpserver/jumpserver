# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from common.permissions import IsValidUser
from common.utils import get_logger
from .. import serializers
from ..models import Preference

logger = get_logger(__file__)


class PreferenceApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsValidUser,)
    queryset = Preference.objects.all()
    serializer_class_mapper = {
        'lina': serializers.LinaSerializer,
        'luna': serializers.LunaSerializer,
        'koko': serializers.KokoSerializer,
    }

    def check_permissions(self, request):
        if self.category not in self.serializer_class_mapper:
            return self.permission_denied(request, 'category is invalid')
        return super().check_permissions(request)

    @property
    def user(self):
        return self.request.user

    @property
    def category(self):
        return self.request.query_params.get('category')

    def get_serializer_class(self):
        cls = self.serializer_class_mapper.get(self.category)
        return cls

    def get_field_defaults(self, serializer):
        field_defaults = {}
        fields = serializer.get_fields()
        for name, field in fields.items():
            if isinstance(field, Serializer):
                field_defaults[name] = self.get_field_defaults(field)
                continue
            default = getattr(field, 'default', None)
            setting_name = self.get_default_setting_name(name)
            field_defaults[name] = getattr(settings, setting_name, default)
        return field_defaults

    def get_default_setting_name(self, field_name):
        if self.category == 'lina' and field_name == 'lang':
            return 'LANGUAGE_CODE'
        if self.category == 'luna':
            return f'LUNA_DEFAULT_{field_name.upper()}'
        return ''

    def get_encrypted_fields(self, serializer):
        encrypted_fields = []
        fields = serializer.get_fields()
        for name, field in fields.items():
            if isinstance(field, Serializer):
                encrypted_fields += self.get_encrypted_fields(field)
                continue
            if not field.write_only:
                continue
            encrypted_fields.append(name)
        return encrypted_fields

    def get_field_names(self, serializer):
        field_names = []
        for name, field in serializer.get_fields().items():
            if isinstance(field, Serializer):
                field_names += self.get_field_names(field)
                continue
            field_names.append(name)
        return field_names

    def get_object(self):
        serializer = self.get_serializer_class()()
        field_defaults = self.get_field_defaults(serializer)

        qs = self.queryset.filter(user=self.user, category=self.category)
        if not qs.exists():
            return field_defaults

        data = dict(qs.values_list('name', 'value'))
        for k, v in data.items():
            for d in field_defaults.values():
                if k in d:
                    d[k] = v
                    break
        return field_defaults

    def perform_update(self, serializer):
        user = self.user
        category = self.category
        model = self.queryset.model
        encrypted_fields = self.get_encrypted_fields(serializer)
        data = serializer.validated_data
        for d in data.values():
            for name, value in d.items():
                kwargs = {'name': name, 'user': user}
                defaults = {'category': category}
                if name in encrypted_fields:
                    value = model.encrypt(value)
                    defaults['encrypted'] = True
                defaults['value'] = value
                defaults.update(kwargs)
                model.objects.update_or_create(defaults, **kwargs)

    def delete(self, request, *args, **kwargs):
        names = request.data.get('names', [])
        if isinstance(names, str):
            names = [names]
        if not isinstance(names, (list, tuple)) or not all(isinstance(name, str) for name in names):
            raise ValidationError({'names': _('Invalid preference fields')})

        serializer = self.get_serializer_class()()
        valid_names = set(self.get_field_names(serializer))
        invalid_names = set(names) - valid_names
        if invalid_names:
            raise ValidationError({'names': _('Invalid preference fields')})

        self.queryset.filter(
            user=self.user, category=self.category, name__in=names
        ).delete()
        data = self.get_serializer(self.get_object()).data
        return Response(data)
