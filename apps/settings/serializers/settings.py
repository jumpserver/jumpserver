# coding: utf-8
from django.core.cache import cache
from django.utils import translation
from django.utils.translation import gettext_noop, gettext_lazy as _

from common.utils import i18n_fmt
from .auth import (
    LDAPSettingSerializer, OIDCSettingSerializer, KeycloakSettingSerializer,
    CASSettingSerializer, RadiusSettingSerializer, FeiShuSettingSerializer,
    WeComSettingSerializer, DingTalkSettingSerializer, AlibabaSMSSettingSerializer,
    TencentSMSSettingSerializer, CMPP2SMSSettingSerializer, AuthSettingSerializer,
    SAML2SettingSerializer, OAuth2SettingSerializer, PasskeySettingSerializer,
    CustomSMSSettingSerializer,
)
from .basic import BasicSettingSerializer
from .cleaning import CleaningSerializer
from .msg import EmailSettingSerializer, EmailContentSettingSerializer
from .other import OtherSettingSerializer
from .security import SecuritySettingSerializer
from .terminal import TerminalSettingSerializer

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
    CleaningSerializer,
    AlibabaSMSSettingSerializer,
    TencentSMSSettingSerializer,
    CMPP2SMSSettingSerializer,
    CustomSMSSettingSerializer,
    PasskeySettingSerializer
):
    CACHE_KEY = 'SETTING_FIELDS_MAPPING'

    # encrypt_fields 现在使用 write_only 来判断了
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields_label_mapping = None

    # 单次计算量不大，搞个缓存，以防操作日志大量写入时，这里影响性能
    def get_field_label(self, field_name):
        self.fields_label_mapping = cache.get(self.CACHE_KEY, None)
        if self.fields_label_mapping is None:
            self.fields_label_mapping = {}
            with translation.override('en'):
                for subclass in SettingsSerializer.__bases__:
                    prefix = getattr(subclass, 'PREFIX_TITLE', _('Setting'))
                    fields = subclass().get_fields()
                    for name, item in fields.items():
                        label = getattr(item, 'label', '')
                        detail = i18n_fmt(gettext_noop('[%s] %s'), prefix, label)
                        self.fields_label_mapping[name] = detail
            cache.set(self.CACHE_KEY, self.fields_label_mapping, 3600 * 24)
        return self.fields_label_mapping.get(field_name)
