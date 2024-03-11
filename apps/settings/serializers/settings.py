from django.core.cache import cache
from django.utils import translation
from django.utils.translation import gettext_noop, gettext_lazy as _
from rest_framework import serializers

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
    'BaseSerializerWithFieldLabel',
    'SettingsSerializer',
]


class BaseSerializerWithFieldLabel:
    CACHE_KEY: str
    ignore_iter_fields = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields_label_mapping = None

    def extract_fields(self, serializer):
        fields = {}
        for field_name, field in serializer.get_fields().items():
            if isinstance(field, serializers.Serializer):
                fields.update(self.extract_fields(field))
            else:
                fields.update({field_name: field})
        return fields

    def get_field_label(self, field_name):
        self.fields_label_mapping = cache.get(self.CACHE_KEY, None)
        if self.fields_label_mapping is None:
            self.fields_label_mapping = {}
            with translation.override('en'):
                cls = self.__class__
                base_name = getattr(cls, 'PREFIX_TITLE', cls.__name__)

                for subclass in cls.__bases__:
                    ignore_iter_fields = getattr(subclass, 'ignore_iter_fields', False)
                    if ignore_iter_fields:
                        continue

                    prefix = getattr(subclass, 'PREFIX_TITLE', base_name)
                    fields = self.extract_fields(subclass())
                    for name, item in fields.items():
                        label = getattr(item, 'label', '')
                        detail = i18n_fmt(gettext_noop('[%s] %s'), prefix, label)
                        self.fields_label_mapping[name] = detail
            cache.set(self.CACHE_KEY, self.fields_label_mapping, 3600 * 24)
        return self.fields_label_mapping.get(field_name, field_name)


class SettingsSerializer(
    BaseSerializerWithFieldLabel,
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
    PREFIX_TITLE = _('Setting')
    CACHE_KEY = 'SETTING_FIELDS_MAPPING'
