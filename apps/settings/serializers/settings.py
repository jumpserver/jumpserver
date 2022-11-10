# coding: utf-8
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

from .basic import BasicSettingSerializer
from .other import OtherSettingSerializer
from .email import EmailSettingSerializer, EmailContentSettingSerializer
from .auth import (
    LDAPSettingSerializer, OIDCSettingSerializer, KeycloakSettingSerializer,
    CASSettingSerializer, RadiusSettingSerializer, FeiShuSettingSerializer,
    WeComSettingSerializer, DingTalkSettingSerializer, AlibabaSMSSettingSerializer,
    TencentSMSSettingSerializer, CMPP2SMSSettingSerializer, AuthSettingSerializer,
    SAML2SettingSerializer, OAuth2SettingSerializer, SSOSettingSerializer
)
from .terminal import TerminalSettingSerializer
from .security import SecuritySettingSerializer
from .cleaning import CleaningSerializer


__all__ = [
    'SettingsSerializer',
]


class SettingsSerializer(
    BasicSettingSerializer,
    LDAPSettingSerializer,
    AuthSettingSerializer,
    TerminalSettingSerializer,
    SecuritySettingSerializer,
    WeComSettingSerializer,
    DingTalkSettingSerializer,
    FeiShuSettingSerializer,
    EmailSettingSerializer,
    EmailContentSettingSerializer,
    OtherSettingSerializer,
    OIDCSettingSerializer,
    SAML2SettingSerializer,
    OAuth2SettingSerializer,
    KeycloakSettingSerializer,
    CASSettingSerializer,
    RadiusSettingSerializer,
    SSOSettingSerializer,
    CleaningSerializer,
    AlibabaSMSSettingSerializer,
    TencentSMSSettingSerializer,
    CMPP2SMSSettingSerializer,
):
    CACHE_KEY = 'SETTING_FIELDS_MAPPING'

    # encrypt_fields 现在使用 write_only 来判断了
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields_label_mapping = None

    # 单次计算量不大，搞个缓存，以防操作日志大量写入时，这里影响性能
    def get_field_label(self, field_name):
        if self.fields_label_mapping is None:
            self.fields_label_mapping = {}
            for subclass in SettingsSerializer.__bases__:
                prefix = getattr(subclass, 'PREFIX_TITLE', _('Setting'))
                fields = subclass().get_fields()
                for name, item in fields.items():
                    label = '[%s] %s' % (prefix, getattr(item, 'label', ''))
                    self.fields_label_mapping[name] = label
            cache.set(self.CACHE_KEY, self.fields_label_mapping, 3600 * 24)
        return self.fields_label_mapping.get(field_name)
