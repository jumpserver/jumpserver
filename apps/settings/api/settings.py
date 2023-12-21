# -*- coding: utf-8 -*-
#

from django.conf import settings
from django.http import HttpResponse
from django.views.static import serve
from rest_framework import generics
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.utils import get_logger
from jumpserver.conf import Config
from rbac.permissions import RBACPermission
from .. import serializers
from ..models import Setting
from ..signals import category_setting_updated
from ..utils import get_interface_setting_or_default

logger = get_logger(__file__)


class SettingsApi(generics.RetrieveUpdateAPIView):
    permission_classes = (RBACPermission,)

    serializer_class_mapper = {
        'all': serializers.SettingsSerializer,
        'basic': serializers.BasicSettingSerializer,
        'terminal': serializers.TerminalSettingSerializer,
        'security': serializers.SecuritySettingSerializer,
        'security_auth': serializers.SecurityAuthSerializer,
        'security_basic': serializers.SecurityBasicSerializer,
        'security_session': serializers.SecuritySessionSerializer,
        'security_password': serializers.SecurityPasswordRuleSerializer,
        'security_login_limit': serializers.SecurityLoginLimitSerializer,
        'ldap': serializers.LDAPSettingSerializer,
        'email': serializers.EmailSettingSerializer,
        'email_content': serializers.EmailContentSettingSerializer,
        'wecom': serializers.WeComSettingSerializer,
        'dingtalk': serializers.DingTalkSettingSerializer,
        'feishu': serializers.FeiShuSettingSerializer,
        'slack': serializers.SlackSettingSerializer,
        'auth': serializers.AuthSettingSerializer,
        'oidc': serializers.OIDCSettingSerializer,
        'keycloak': serializers.KeycloakSettingSerializer,
        'radius': serializers.RadiusSettingSerializer,
        'cas': serializers.CASSettingSerializer,
        'saml2': serializers.SAML2SettingSerializer,
        'oauth2': serializers.OAuth2SettingSerializer,
        'passkey': serializers.PasskeySettingSerializer,
        'clean': serializers.CleaningSerializer,
        'other': serializers.OtherSettingSerializer,
        'sms': serializers.SMSSettingSerializer,
        'alibaba': serializers.AlibabaSMSSettingSerializer,
        'tencent': serializers.TencentSMSSettingSerializer,
        'huawei': serializers.HuaweiSMSSettingSerializer,
        'cmpp2': serializers.CMPP2SMSSettingSerializer,
        'custom': serializers.CustomSMSSettingSerializer,
        'vault': serializers.VaultSettingSerializer,
        'chat': serializers.ChatAISettingSerializer,
        'announcement': serializers.AnnouncementSettingSerializer,
        'ticket': serializers.TicketSettingSerializer,
        'ops': serializers.OpsSettingSerializer,
        'virtualapp': serializers.VirtualAppSerializer,
    }

    rbac_category_permissions = {
        'basic': 'settings.view_setting',
        'terminal': 'settings.change_terminal',
        'ops': 'settings.change_ops',
        'ticket': 'settings.change_ticket',
        'virtualapp': 'settings.change_virtualapp',
        'announcement': 'settings.change_announcement',
        'security': 'settings.change_security',
        'security_basic': 'settings.change_security',
        'security_auth': 'settings.change_security',
        'security_session': 'settings.change_security',
        'security_password': 'settings.change_security',
        'security_login_limit': 'settings.change_security',
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
        'oauth2': 'settings.change_auth',
        'clean': 'settings.change_clean',
        'other': 'settings.change_other',
        'sms': 'settings.change_sms',
        'alibaba': 'settings.change_sms',
        'tencent': 'settings.change_sms',
        'vault': 'settings.change_vault',
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

    def send_signal(self, serializer):
        category = self.request.query_params.get('category', '')
        category_setting_updated.send(sender=self.__class__, category=category, serializer=serializer)

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
        self.send_signal(serializer)


class SettingsLogoApi(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        size = request.GET.get('size', 'small')
        interface_data = get_interface_setting_or_default()
        if size == 'small':
            logo_path = interface_data['logo_logout']
        else:
            logo_path = interface_data['logo_index']

        if logo_path.startswith('/media/'):
            logo_path = logo_path.replace('/media/', '')
            document_root = settings.MEDIA_ROOT
        elif logo_path.startswith('/static/'):
            logo_path = logo_path.replace('/static/', '/')
            document_root = settings.STATIC_ROOT
        else:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        return serve(request, logo_path, document_root=document_root)
