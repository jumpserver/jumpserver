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
        'oauth2': serializers.OAuth2SettingSerializer,
        'clean': serializers.CleaningSerializer,
        'other': serializers.OtherSettingSerializer,
        'sms': serializers.SMSSettingSerializer,
        'alibaba': serializers.AlibabaSMSSettingSerializer,
        'tencent': serializers.TencentSMSSettingSerializer,
        'huawei': serializers.HuaweiSMSSettingSerializer,
        'cmpp2': serializers.CMPP2SMSSettingSerializer,
    }

    rbac_category_permissions = {
        'basic': 'settings.view_setting',
        'terminal': 'settings.change_terminal',
        'security': 'settings.change_security',
        'ldap': 'settings.change_auth',
        'email': 'settings.change_email',
        'email_content': 'settings.change_email',
        'wecom': 'settings.change_auth',
        'dingtalk': 'settings.change_auth',
        'feishu': 'settings.change_auth',
        'auth': 'settings.change_auth',
        'oidc': 'settings.change_auth',
        'keycloak': 'settings.change_auth',
        'radius': 'settings.change_auth',
        'cas': 'settings.change_auth',
        'sso': 'settings.change_auth',
        'saml2': 'settings.change_auth',
        'clean': 'settings.change_clean',
        'other': 'settings.change_other',
        'sms': 'settings.change_sms',
        'alibaba': 'settings.change_sms',
        'tencent': 'settings.change_sms',
    }

    def get_queryset(self):
        return Setting.objects.all()

    def check_permissions(self, request):
        category = request.query_params.get('category', 'basic')
        perm_required = self.rbac_category_permissions.get(category)
        has = self.request.user.has_perm(perm_required)

        if not has:
            self.permission_denied(request)

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
        post_data_names = list(self.request.data.keys())
        settings_items = self.parse_serializer_data(serializer)
        serializer_data = getattr(serializer, 'data', {})
        for item in settings_items:
            if item['name'] not in post_data_names:
                continue
            changed, setting = Setting.update_or_create(**item)
            if not changed:
                continue
            serializer_data[setting.name] = setting.cleaned_value
        setattr(serializer, '_data', serializer_data)
        if hasattr(serializer, 'post_save'):
            serializer.post_save()
