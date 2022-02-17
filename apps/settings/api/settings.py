# -*- coding: utf-8 -*-
#

from rest_framework import generics
from django.conf import settings

from jumpserver.conf import Config
from rbac.permissions import RBACPermission
from common.utils import get_logger
from .. import serializers
from ..models import Setting

logger = get_logger(__file__)


class SettingsApi(generics.RetrieveUpdateAPIView):
    permission_classes = (RBACPermission,)

    serializer_class_mapper = {
        'all': serializers.SettingsSerializer,
        'basic': serializers.BasicSettingSerializer,
        'terminal': serializers.TerminalSettingSerializer,
        'security': serializers.SecuritySettingSerializer,
        'ldap': serializers.LDAPSettingSerializer,
        'email': serializers.EmailSettingSerializer,
        'email_content': serializers.EmailContentSettingSerializer,
        'wecom': serializers.WeComSettingSerializer,
        'dingtalk': serializers.DingTalkSettingSerializer,
        'feishu': serializers.FeiShuSettingSerializer,
        'auth': serializers.AuthSettingSerializer,
        'oidc': serializers.OIDCSettingSerializer,
        'keycloak': serializers.KeycloakSettingSerializer,
        'radius': serializers.RadiusSettingSerializer,
        'cas': serializers.CASSettingSerializer,
        'sso': serializers.SSOSettingSerializer,
        'saml2': serializers.SAML2SettingSerializer,
        'clean': serializers.CleaningSerializer,
        'other': serializers.OtherSettingSerializer,
        'sms': serializers.SMSSettingSerializer,
        'alibaba': serializers.AlibabaSMSSettingSerializer,
        'tencent': serializers.TencentSMSSettingSerializer,
    }

    def get_queryset(self):
        return Setting.objects.all()

    def get_serializer_class(self):
        category = self.request.query_params.get('category', 'basic')
        default = serializers.BasicSettingSerializer
        cls = self.serializer_class_mapper.get(category, default)
        return cls

    def get_fields(self):
        serializer = self.get_serializer_class()()
        fields = serializer.get_fields()
        return fields

    def get_object(self):
        items = self.get_fields().keys()
        obj = {}
        for item in items:
            if hasattr(settings, item):
                obj[item] = getattr(settings, item)
            else:
                obj[item] = Config.defaults[item]
        return obj

    def parse_serializer_data(self, serializer):
        data = []
        fields = self.get_fields()
        encrypted_items = [name for name, field in fields.items() if field.write_only]
        category = self.request.query_params.get('category', '')
        for name, value in serializer.validated_data.items():
            encrypted = name in encrypted_items
            if encrypted and value in ['', None]:
                continue
            data.append({
                'name': name, 'value': value,
                'encrypted': encrypted, 'category': category
            })
        return data

    def perform_update(self, serializer):
        settings_items = self.parse_serializer_data(serializer)
        serializer_data = getattr(serializer, 'data', {})
        for item in settings_items:
            changed, setting = Setting.update_or_create(**item)
            if not changed:
                continue
            serializer_data[setting.name] = setting.cleaned_value
        setattr(serializer, '_data', serializer_data)
        if hasattr(serializer, 'post_save'):
            serializer.post_save()
