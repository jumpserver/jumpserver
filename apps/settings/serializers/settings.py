# coding: utf-8

from .basic import BasicSettingSerializer
from .other import OtherSettingSerializer
from .email import EmailSettingSerializer, EmailContentSettingSerializer
from .auth import (
    LDAPSettingSerializer, OIDCSettingSerializer, KeycloakSettingSerializer,
    CASSettingSerializer, RadiusSettingSerializer, FeiShuSettingSerializer,
    WeComSettingSerializer, DingTalkSettingSerializer, AlibabaSMSSettingSerializer,
    TencentSMSSettingSerializer, CMPP2SMSSettingSerializer
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
    TerminalSettingSerializer,
    SecuritySettingSerializer,
    WeComSettingSerializer,
    DingTalkSettingSerializer,
    FeiShuSettingSerializer,
    EmailSettingSerializer,
    EmailContentSettingSerializer,
    OtherSettingSerializer,
    OIDCSettingSerializer,
    KeycloakSettingSerializer,
    CASSettingSerializer,
    RadiusSettingSerializer,
    CleaningSerializer,
    AlibabaSMSSettingSerializer,
    TencentSMSSettingSerializer,
    CMPP2SMSSettingSerializer,
):
    # encrypt_fields 现在使用 write_only 来判断了
    pass
